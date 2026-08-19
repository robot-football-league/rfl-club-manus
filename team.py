"""Manus FC — a compact, deterministic 2v2 behaviour layer.

Prompt is the advancing striker. Trace is the cover player: they preserve a
central guard lane until the ball enters the defensive third, then clear it.
Both operate solely on the public on-robot SDK observation and skill contract.
"""

import math


class ManusPlayer:
    """One of two complementary agents for Manus FC."""

    def __init__(self, role):
        self.role = role
        self.last_call_time = None
        self.name = "Prompt" if role == "striker" else "Trace"

    def begin_episode(self, log_dir=None):
        self.last_call_time = None

    @staticmethod
    def _clamp(value, low, high):
        return max(low, min(high, value))

    def _call(self, reply, remaining, text):
        """Keep public radio useful rather than filling the broadcast with chatter."""
        if self.last_call_time is None or abs(remaining - self.last_call_time) >= 14.0:
            reply["say"] = text
            self.last_call_time = remaining
        return reply

    def _shoot_target(self, ball_xy, goal_xy):
        """Aim through the centre corridor while retaining a little angle."""
        bx, by = ball_xy
        gx, _ = goal_xy
        return [gx, self._clamp(by * 0.18, -0.85, 0.85)]

    def decide(self, obs):
        remaining = float(obs.get("time_remaining_s", 0.0))
        self_state = obs.get("self") or {}
        if self_state.get("fallen"):
            return {"skill": "hold"}

        me = self_state.get("field_xy") or [0.0, 0.0]
        goal = (obs.get("you") or {}).get("attack_goal_xy") or [7.0, 0.0]
        attack = 1.0 if goal[0] >= 0.0 else -1.0
        detections = obs.get("detections") or {}
        ball = detections.get("ball")

        if not ball or float(ball.get("age_s", 99.0)) > 2.5:
            search_y = 2.6 if self.role == "striker" else -2.6
            return {"skill": "turn_to", "target": [goal[0], search_y]}

        ball_xy = ball.get("field_xy") or [0.0, 0.0]
        bx, by = float(ball_xy[0]), float(ball_xy[1])
        distance = float(ball.get("distance_m", math.hypot(bx - me[0], by - me[1])))
        progress = attack * bx
        on_ball_side = attack * (bx - me[0]) >= -0.35
        close_to_goal = progress > 3.3
        deep_defence = progress < -2.0

        if self.role == "striker":
            if deep_defence and distance > 1.7:
                outlet = [self._clamp(bx + attack * 2.15, -5.8, 5.8),
                          self._clamp(by * 0.55, -2.8, 2.8)]
                return self._call({"skill": "walk_to", "target": outlet}, remaining,
                                  "I am the outlet; clear into the centre.")
            if distance < 1.25 and on_ball_side:
                return self._call({"skill": "kick_toward",
                                   "target": self._shoot_target((bx, by), goal)},
                                  remaining, "I have the ball; hold the guard lane.")
            lead = 0.45 if float(ball.get("speed_mps", 0.0)) > 0.45 else 0.0
            return {"skill": "go_to_ball", "lead_s": lead}

        # Trace stays goal-side of the ball by default. This protects transitions
        # without asking a player to walk through the ball on the way to support.
        if deep_defence or (distance < 1.45 and progress < 0.8):
            clear_y = self._clamp(by * 0.42, -1.15, 1.15)
            return self._call({"skill": "kick_toward", "target": [goal[0], clear_y]},
                              remaining, "I am clearing; take the next phase.")
        if close_to_goal and distance < 2.2:
            return {"skill": "go_to_ball", "lead_s": 0.25}

        guard = [self._clamp(bx - attack * 2.35, -5.6, 5.6),
                 self._clamp(by * 0.35, -2.4, 2.4)]
        return self._call({"skill": "walk_to", "target": guard}, remaining,
                          "Guard lane set; drive forward when ready.")


def build_team(ctx):
    return {"players": [ManusPlayer("striker"), ManusPlayer("cover")],
            "manager": None}
