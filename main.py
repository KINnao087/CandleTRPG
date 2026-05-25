from backend.app.ai import resolve_turn
from backend.app.domain.action import PlayerAction
from backend.app.domain.context import Scene
from backend.app.services.context_manager import ContextManager


def build_initial_world() -> str:
    return (
        "这是一个近未来都市背景的局域网跑团。旧城区被企业、帮派和地下情报贩子共同控制。"
        "AI 主持人需要保持剧情集中在当前场景，只结算玩家本轮行动造成的直接结果。"
    )


def build_initial_scene() -> Scene:
    return Scene.from_dict({
        "time": "夜晚 21:30",
        "location": "MIX 酒馆",
        "description": (
            "酒馆里很安静，窗外的霓虹招牌时明时暗。吧台后方有一扇狭窄的后门，"
            "门后通向一条没有监控的暗巷。"
        ),
    })


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
    context = ContextManager(
        world=build_initial_world(),
        scene=build_initial_scene(),
        characters=build_initial_characters(),
    )
    turn_index = 1

    print("CandleTRPG-LAN 命令行跑团演示")
    print("输入 q 退出。")

    while True:
        print()
        print(f"===== 第 {turn_index} 回合 =====")
        print_scene(context.scene)

        action_text = input("\n请输入你的行动：").strip()
        if action_text.lower() in {"q", "quit", "exit"}:
            print("跑团结束。")
            break

        if not action_text:
            print("行动不能为空。")
            continue

        actions: list[PlayerAction] = [
            {
                "player_id": "player_001",
                "character_name": context.characters[0]["name"],
                "action_text": action_text,
            }
        ]

        ai_context = context.build_ai_context()

        try:
            result = resolve_turn(
                world=ai_context["world"],
                scene=ai_context["scene"],
                characters=ai_context["characters"],
                history=ai_context["history"],
                actions=actions,
            )
        except Exception as exc:
            print(f"\nAI 结算失败：{exc}")
            continue

        narration = result.get("narration", "").strip()
        scene = result.get("scene", "")
        if not narration:
            print("\nAI 返回了空旁白。")
            continue

        # print()
        # print("----- 主持人 -----")
        print(narration)

        context.record_turn(
            turn_index=turn_index,
            actions=actions,
            narration=narration,
            scene=scene,
        )

        print("历史：：：：：：：：")
        print(context.turn_history)
        print("：：：：：：：：：：")

        turn_index += 1


if __name__ == "__main__":
    main()
