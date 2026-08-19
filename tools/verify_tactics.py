"""Exercise Manus FC's behaviour decisions against representative SDK inputs."""

import team


def observation(position, ball, remaining=60.0):
    return {
        "time_remaining_s": remaining,
        "self": {"field_xy": position, "fallen": False},
        "you": {"attack_goal_xy": [7.0, 0.0]},
        "detections": {"ball": ball, "teammates": [], "opponents": []},
    }


def ball(x, y, distance, age=0.0, speed=0.0):
    return {"field_xy": [x, y], "distance_m": distance, "age_s": age,
            "speed_mps": speed}


def main():
    prompt, trace = team.build_team({"team_index": 0, "config": {}})["players"]
    prompt.begin_episode()
    trace.begin_episode()

    cases = [
        ("Prompt attacks a visible central ball", prompt,
         observation([-2.5, 1.2], ball(0.0, 0.0, 2.8)), "go_to_ball"),
        ("Trace establishes a goal-side guard lane", trace,
         observation([-2.5, -1.2], ball(0.0, 0.0, 2.8)), "walk_to"),
        ("Trace clears a ball in the defensive third", trace,
         observation([-3.0, -0.4], ball(-3.2, 0.5, 0.5)), "kick_toward"),
        ("Prompt finishes from the ball side", prompt,
         observation([-0.7, 0.0], ball(0.0, 0.0, 0.7)), "kick_toward"),
        ("Prompt scans when the ball memory is stale", prompt,
         observation([0.0, 0.0], ball(0.0, 0.0, 1.0, age=3.0)), "turn_to"),
    ]

    for label, player, obs, expected in cases:
        reply = player.decide(obs)
        actual = reply.get("skill")
        if actual != expected:
            raise AssertionError(f"{label}: expected {expected}, got {actual}")
        print(f"PASS: {label} -> {actual}")


if __name__ == "__main__":
    main()
