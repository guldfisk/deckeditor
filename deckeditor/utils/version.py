from deckeditor import values
from deckeditor.context.context import Context


def version_formatted() -> str:
    return f'{values.APPLICATION_NAME} {values.VERSION}{" (debug)" if Context.debug else ""}'
