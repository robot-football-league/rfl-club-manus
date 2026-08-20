"""Manus FC — an adaptive, role-specific behaviour layer for RFL 0.3.

Round one showed that a fixed striker/cover split left both robots detached from
late defensive emergencies. The new design assigns both players a fast registered
frontier decision model, then enforces only a small set of deterministic safety
rails: emergency clearance, wall escape, stale-ball search, and invalid-reply
recovery. It uses only the published SDK observation and skill interface.
"""

import math

from gauntlet.football import make_football_agent


MODEL = "llm:openai:gpt-5.6-luna"


ROLE_BRIEFS = {
    "prompt": """
# Manus FC role: Prompt, the front-foot finisher
You are Prompt. Be the first attacker, but do not merely chase. On a visible
ball, judge whether you are ball-side, whether a direct goal push is available,
and whether the ball is trapped on a wall. Attack the centre of the goal when
close; use a reachable wall release rather than pinning it. If play is deep in
our half, become an outlet only after Trace is close enough to contest danger.
Do not stand still while the ball is live. Use public radio only for a genuine
state change: pressing, wall release, or an emergency clear.
""",
    "trace": """
# Manus FC role: Trace, the adaptive sweeper
You are Trace. Your priority is not a fixed spot: stay ball-side and goal-side
of the live danger. When the ball enters our defensive third, contest it and
clear toward the opponent goal. When play is stable, hold a compact central
screen one to two metres behind the ball rather than remaining at midfield.
When the ball reaches a wall, choose a reachable release angle and be ready to
engage, not merely to narrate cover. Join the attack only after the central
lane is secure. Use public radio only to signal an actual clear, wall case, or
emergency.
""",
}


class AdaptiveManusPlayer:
    """LLM-led player with legal, local safety rails around the SDK skills."""

    def __init__(self, role, index):
        self.role = role
        self.name = "Prompt" if role == "prompt" else "Trace"
        self.agent = make_football_agent(MODEL, index, seed=index,
                                         prompt="football_v2")
        self.agent.reply_keys = None
        self.agent.history_n = 6
        self.agent.max_output = 160
        self.agent.system_prompt += ROLE_BRIEFS[role]
        self.last_call_time = None

    def begin_episode(self, log_dir=None):
        self.last_call_time = None
        self.agent.begin_episode(log_dir=log_dir)

    @staticmethod
    def _clamp(value, low, high):
        return max(low, min(high, value))

    def _say(self, reply, obs, text):
        remaining = float(obs.get("time_remaining_s", 0.0))
        if self.last_call_time is None or abs(remaining - self.last_call_time) >= 16.0:
            reply["say"] = text
            self.last_call_time = remaining
        return reply

    def _context(self, obs):
        self_state = obs.get("self") or {}
        ball = (obs.get("detections") or {}).get("ball")
        goal = (obs.get("you") or {}).get("attack_goal_xy") or [7.0, 0.0]
        attack = 1.0 if float(goal[0]) >= 0.0 else -1.0
        if not ball or float(ball.get("age_s", 99.0)) > 2.5:
            return self_state, None, goal, attack, 0.0, 0.0, 99.0
        point = ball.get("field_xy") or [0.0, 0.0]
        bx, by = float(point[0]), float(point[1])
        distance = float(ball.get("distance_m", 99.0))
        return self_state, ball, goal, attack, bx, by, distance

    def _fallback(self, obs, reason):
        self_state, ball, goal, attack, bx, by, distance = self._context(obs)
        if self_state.get("fallen"):
            return {"skill": "hold"}
        if ball is None:
            search_y = 2.8 if self.role == "prompt" else -2.8
            return self._say({"skill": "turn_to", "target": [0.0, search_y]}, obs,
                             "Ball lost; resetting the central scan.")
        progress = attack * bx
        if distance < 1.25:
            target = [goal[0], self._clamp(by * 0.22, -0.9, 0.9)]
            return self._say({"skill": "kick_toward", "target": target}, obs,
                             "Clearing the live danger.")
        if self.role == "prompt":
            return {"skill": "go_to_ball", "lead_s": 0.35}
        guard = [self._clamp(bx - attack * 1.65, -5.8, 5.8),
                 self._clamp(by * 0.35, -2.3, 2.3)]
        if progress < -1.8 or distance < 2.2:
            return {"skill": "go_to_ball", "lead_s": 0.25}
        return {"skill": "walk_to", "target": guard}

    def _emergency(self, obs):
        self_state, ball, goal, attack, bx, by, distance = self._context(obs)
        if self_state.get("fallen"):
            return {"skill": "hold"}
        if ball is None:
            return None
        progress = attack * bx
        wall_case = bool(ball.get("against_wall"))
        stuck_for = float((obs.get("referee") or {}).get("ball_stuck_s", 0.0))
        # A direct clearance is mandatory when a nearby ball reaches the final
        # defensive third. This corrects the 339 defensive-half seconds and 11
        # concessions recorded in round one without replacing normal play.
        if progress < -3.4 and distance < 2.7:
            target = [goal[0], self._clamp(by * 0.32, -1.0, 1.0)]
            return self._say({"skill": "kick_toward", "target": target}, obs,
                             "Emergency clear; reset behind the ball.")
        if wall_case and stuck_for >= 2.0 and distance < 2.0:
            target = [goal[0], self._clamp(by * 0.55, -1.3, 1.3)]
            return self._say({"skill": "kick_toward", "target": target}, obs,
                             "Wall case; releasing along the reachable lane.")
        return None

    @staticmethod
    def _legal_skill(reply):
        return (isinstance(reply, dict)
                and reply.get("skill") in {"go_to_ball", "kick_toward",
                                            "walk_to", "turn_to", "hold"})

    def decide(self, obs):
        emergency = self._emergency(obs)
        if emergency is not None:
            return emergency
        self_state, ball, _, _, _, _, _ = self._context(obs)
        if ball is None and not self_state.get("fallen"):
            return self._fallback(obs, "lost")
        reply = self.agent.decide(obs)
        if not self._legal_skill(reply):
            return self._fallback(obs, "invalid")
        # Holding is not a valid answer to a fresh, live ball unless a player
        # has fallen; force a controlled re-engagement instead.
        self_state, ball, _, _, _, _, _ = self._context(obs)
        if (reply.get("skill") == "hold" and ball is not None
                and not self_state.get("fallen")):
            return self._fallback(obs, "passive")
        return reply


def build_team(ctx):
    base = int(ctx.get("team_index", 0)) * 2
    return {"players": [AdaptiveManusPlayer("prompt", base),
                        AdaptiveManusPlayer("trace", base + 1)],
            "manager": None}
