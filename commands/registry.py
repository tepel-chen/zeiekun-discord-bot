from commands.archive import register_command as register_archive_command
from commands.chal import register_command as register_chal_command
from commands.ctfconf import register_command as register_ctfconf_command
from commands.create import register_command as register_create_command
from commands.disclose import register_command as register_disclose_command
from commands.help import register_command as register_help_command
from commands.leave import register_command as register_leave_command
from commands.players import register_command as register_players_command
from commands.randomname import register_command as register_randomname_command
from commands.search import register_command as register_search_command
from commands.solve import register_command as register_solve_command
from commands.switchteam import register_command as register_switchteam_command
from commands.time import register_command as register_time_command


COMMAND_REGISTRARS = [
    register_help_command,
    register_create_command,
    register_disclose_command,
    register_ctfconf_command,
    register_archive_command,
    register_chal_command,
    register_leave_command,
    register_players_command,
    register_randomname_command,
    register_solve_command,
    register_switchteam_command,
    register_search_command,
    register_time_command,
]


def register_commands(ctf_commands, context):
    for register_command in COMMAND_REGISTRARS:
        register_command(ctf_commands, context)
