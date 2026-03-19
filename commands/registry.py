from commands.archive import register_command as register_archive_command
from commands.chal import register_command as register_chal_command
from commands.create import register_command as register_create_command
from commands.search import register_command as register_search_command
from commands.solve import register_command as register_solve_command


def register_commands(ctf_commands, context):
    register_create_command(ctf_commands, context)
    register_archive_command(ctf_commands, context)
    register_chal_command(ctf_commands, context)
    register_solve_command(ctf_commands, context)
    register_search_command(ctf_commands, context)
