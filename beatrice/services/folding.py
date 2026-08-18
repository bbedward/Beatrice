import asyncio

from beatrice.services.prices import json_get

BANANO_TEAM_ID = 234980

CHECK = "<:white_check_mark:835347973503451176>"
CROSS = "<:x:835354642308661278>"
NOTE = "<:grey_exclamation:835357988432642049>"
BANANA = "<:banana:838483242113957898>"
CLICKER = "<:arrow_right:856238567713800222> Click here for: "

PASSKEY_INFO = (
    "[Passkey Bonus Info](https://foldingathome.org/support/faq/points/?lng=en-US"
    "#what-are-the-qualifications-for-the-qrb)\n"
    "Passkey Requires 10 work units completed after adding to client to activate."
)


def valid_username(username: str) -> bool:
    return 5 <= len(username) <= 20 and username.isalnum()


async def fetch_user_data(username: str) -> tuple[dict, dict, list]:
    fah, bminer, bonus = await asyncio.gather(
        json_get(f"https://api2.foldingathome.org/user/{username}"),
        json_get(f"https://bananominer.com/user_name/{username}"),
        json_get(f"https://api2.foldingathome.org/bonus?user={username}"),
    )
    return fah or {}, bminer or {}, bonus or []


def build_report(username: str, fah: dict, bminer: dict, bonus: list) -> str | None:
    if not bminer or not fah:
        return None

    output = ""
    correct = True

    if "error" in bminer:
        output += (
            f"{CROSS} {username} not a valid Bananominer username.\n"
            "Update username by putting banano wallet address into <https://bananominer.com/> "
            "and copy/pasting into folding at home client \n"
        )
        correct = False
    else:
        output += f"{CHECK} {username} is a valid bananominer username\n"

    ban_team = {}
    non_ban_wus = 0
    if "name" not in fah or "teams" not in fah:
        output += f'{CROSS} User "{username}" has not completed a Work Unit\n'
        correct = False
    else:
        for team in fah["teams"]:
            if team["team"] == BANANO_TEAM_ID and "wus" in team:
                ban_team = team
            elif "wus" in team:
                non_ban_wus += team["wus"]
        if not ban_team:
            output += (
                f'{CROSS} User: "{username}" has not folded for banano team ID {BANANO_TEAM_ID}\n'
            )
            correct = False

    if correct:
        if "last" in ban_team:
            output += f"{CHECK} {ban_team['last']} UTC : Last Completed Banano WU\n"
        output += f"{CHECK} {ban_team['wus']} work units completed so far.\n"
        output += f"{CHECK} {ban_team['score']} points received so far.\n"
        payments = bminer["payments"]
        if not payments:
            output += (
                f"{NOTE} No payments sent yet. First payment is within 24-36 hours of completing "
                "first Work Unit as long as you complete at least 2 work units (progress bar going "
                "to 100%) with at least one in each 12 hour period.\n"
            )
            output += f"{BANANA}Work Units Pending Payment: {ban_team['wus']}\n"
            output += f"{BANANA}Points Pending Payment: {ban_team['score']}\n"
        else:
            output += f"{CHECK} {payments[0]['created_at']} UTC was latest payment for user.\n"
            output += (
                f"{BANANA}Work Units Pending Payment: "
                f"{ban_team['wus'] - payments[0]['work_units']}\n"
            )
            output += (
                f"{BANANA}Points Pending Payment: {ban_team['score'] - payments[0]['score']}\n"
            )

        active_bonus = any(cpu["active"] == 1 for cpu in bonus)
        if active_bonus:
            output += f"{CHECK} Passkey Bonus Active\n"
        elif bonus:
            output += (
                f"{NOTE}  Passkey Bonus     Not Active, but appears to be in progress\n"
                f"{CLICKER}{PASSKEY_INFO}"
            )
        else:
            output += (
                f"{NOTE}  Passkey Bonus     Not Active and does not appear to be entered \n"
                " <:arrow_right:856238567713800222> Click here to: "
                "[Get a Passkey](https://apps.foldingathome.org/getpasskey)\n"
                f"{CLICKER}{PASSKEY_INFO}"
            )

    if non_ban_wus > 0:
        output += (
            f"{NOTE} {username} has completed {non_ban_wus} number of Work Units "
            "for teams other than Banano\n"
        )
    if not correct:
        output += (
            "\nPlease review above errors. After updating client and completing another Work "
            "Unit: this test can be ran again to verify your client is set up to track points "
            "correctly.\n"
        )

    output += "\n"
    if "id" in fah:
        output += (
            f"{CLICKER}[F@H Donor Stat Page](https://stats.foldingathome.org/donor/{fah['id']}) \n"
        )
    output += f"{CLICKER}[Bananominer JSON Stats](https://bananominer.com/user_name/{username})\n"
    output += "FODL Check might be cached and may not update immediately.\n"
    return output
