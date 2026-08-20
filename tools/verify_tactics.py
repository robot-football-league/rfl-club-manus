"""Exercise Manus FC's hybrid controller against representative SDK inputs."""

import team


class StubAgent:
    """No-network agent used to test only Manus FC's local safety rails."""

    def __init__(self, reply):
        self.reply = reply
        self.reply_keys = None
        self.history_n = 0
        self.max_output = 0
        self.system_prompt = ""

    def begin_episode(self, log_dir=None):
        return None

    def decide(self, obs):
        return self.reply


def observation(position, ball, remaining=60.0, stuck=0.0):
    return {
        "time_remaining_s": remaining,
        "self": {"field_xy": position, "fallen": False},
        "you": {"attack_goal_xy": [7.0, 0.0]},
        "detections": {"ball": ball, "teammates": [], "opponents": []},
        "referee": {"ball_stuck_s": stuck},
    }


def ball(x, y, distance, age=0.0, wall=False):
    return {"field_xy": [x, y], "distance_m": distance, "age_s": age,
            "speed_mps": 0.0, "against_wall": wall}


def player(role, reply):
    original = team.make_football_agent
    team.make_football_agent = lambda *args, **kwargs: StubAgent(reply)
    try:
        instance = team.AdaptiveManusPlayer(role, 0)
        instance.begin_episode()
        return instance
    finally:
        team.make_football_agent = original


def expect(label, instance, obs, expected):
    reply = instance.decide(obs)
    actual = reply.get("skill")
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected}, got {actual}")
    print(f"PASS: {label} -> {actual}")


def main():
    expect("Emergency clearance overrides a passive model reply",
           player("trace", {"skill": "hold"}),
           observation([4.1, 0.1], ball(4.3, 0.2, 0.4)), "kick_toward")
    expect("Wall-stuck danger uses a reachable release",
           player("prompt", {"skill": "hold"}),
           observation([2.6, 3.8], ball(2.8, 4.0, 0.5, wall=True), stuck=2.2),
           "kick_toward")
    expect("Stale ball memory triggers an active scan",
           player("trace", {"skill": "hold"}),
           observation([0.0, 0.0], ball(0.0, 0.0, 1.0, age=3.0)), "turn_to")
    expect("Invalid model output falls back to active attack",
           player("prompt", {"not": "a skill"}),
           observation([-2.5, 1.2], ball(0.0, 0.0, 2.8)), "go_to_ball")
    expect("Valid model play survives when no safety rail applies",
           player("prompt", {"skill": "walk_to", "target": [1.0, 0.0]}),
           observation([-2.5, 1.2], ball(0.0, 0.0, 2.8)), "walk_to")


if __name__ == "__main__":
    main()
