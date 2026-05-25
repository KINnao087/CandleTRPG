from backend.app.ai import resolve_turn


def build_initial_world() -> str:
    return (
        "这是一个近未来都市背景的局域网跑团。旧城区被企业、帮派和地下情报贩子共同控制。"
        "AI 主持人需要保持剧情集中在当前场景，只结算玩家本轮行动造成的直接结果。"
    )


def build_initial_scene() -> dict:
    return {
        "time": "夜晚 21:30",
        "location": "MIX 酒馆",
        "description": (
            "酒馆里很安静，窗外的霓虹招牌时明时暗。吧台后方有一扇狭窄的后门，"
            "门后通向一条没有监控的暗巷。"
        ),
    }


def build_initial_characters() -> list[dict]:
    return [
        {
            "id": "char_001",
            "player_id": "player_001",
            "name": "林烛",
            "status": {
                "hp": 85,
                "conditions": [],
            },
            "inventory": ["终端", "短刀", "急救喷雾"],
        }
    ]


def print_scene(scene: dict) -> None:
    print()
    print(f"时间：{scene.get('time', '未知')}")
    print(f"地点：{scene.get('location', '未知')}")
    print(scene.get("description", ""))


def main() -> None:
    world = build_initial_world()
    scene = build_initial_scene()
    characters = build_initial_characters()
    recent_summary = ""
    turn_index = 1

    print("CandleTRPG-LAN 命令行跑团演示")
    print("输入 q 退出。")

    while True:
        print()
        print(f"===== 第 {turn_index} 回合 =====")
        print_scene(scene)

        action_text = input("\n请输入你的行动：").strip()
        if action_text.lower() in {"q", "quit", "exit"}:
            print("跑团结束。")
            break

        if not action_text:
            print("行动不能为空。")
            continue

        actions = [
            {
                "player_id": "player_001",
                "character_name": characters[0]["name"],
                "action_text": action_text,
            }
        ]

        try:
            result = resolve_turn(
                world=world,
                scene=scene,
                characters=characters,
                actions=actions,
                recent_summary=recent_summary,
            )
        except Exception as exc:
            print(f"\nAI 结算失败：{exc}")
            continue

        narration = result.get("narration", "").strip()
        if not narration:
            print("\nAI 返回了空旁白。")
            continue

        print()
        print("----- 主持人 -----")
        print(narration)

        recent_summary = narration[-500:]
        scene["description"] = narration
        turn_index += 1


if __name__ == "__main__":
    main()
