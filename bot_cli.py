import argparse
import getpass
import sys
from bot_manager import BotManager

def main():
    parser = argparse.ArgumentParser(description="Manage Chat Analyzer Bots")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Add Bot Command
    add_parser = subparsers.add_parser("add", help="Register a new bot")
    add_parser.add_argument("backend", choices=["telegram", "webex"], help="The chat backend")
    add_parser.add_argument("name", help="A unique name for the bot")
    add_parser.add_argument("user_id", help="The ID of the user registering the bot")

    # List Bots Command
    list_parser = subparsers.add_parser("list", help="List registered bots")
    list_parser.add_argument("user_id", help="The ID of the user whose bots to list")
    list_parser.add_argument("--backend", choices=["telegram", "webex"], help="Filter by backend")

    # Remove Bot Command
    remove_parser = subparsers.add_parser("remove", help="Deregister a bot")
    remove_parser.add_argument("user_id", help="The ID of the user who owns the bot")
    remove_parser.add_argument("backend", choices=["telegram", "webex"], help="The chat backend")
    remove_parser.add_argument("name", help="The name of the bot to remove")

    args = parser.parse_args()
    bot_manager = BotManager()

    if args.command == "add":
        token = getpass.getpass(f"Enter token for {args.name} ({args.backend}): ")
        bot_id = input(f"Enter the bot ID for {args.name}: ")
        try:
            bot_manager.register_bot(args.user_id, args.backend, args.name, token, bot_id)
            print(f"Bot '{args.name}' for {args.backend} registered successfully for user {args.user_id}.")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "list":
        bots = bot_manager.get_bots(args.user_id, args.backend)
        if not bots:
            print(f"No bots found for user {args.user_id}" + (f" on {args.backend}." if args.backend else "."))
            return
        
        print(f"Bots for user {args.user_id}:")
        for bot in bots:
            print(f"  - {bot['name']} ({args.backend or 'all'})")

    elif args.command == "remove":
        try:
            bot_manager.delete_bot(args.user_id, args.backend, args.name)
            print(f"Bot '{args.name}' for {args.backend} has been removed for user {args.user_id}.")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()