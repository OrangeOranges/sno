import json
import io

import click

from .apply import apply_patch
from .cli_util import StringFromFile
from .exceptions import InvalidOperation
from .output_util import dump_json_output, format_json_for_output, resolve_output_path
from .structure import RepositoryStructure

# Changing these items would generally break the repo;
# we disallow that.
READONLY_ITEMS = {
    'primary_key',
    'sqlite_table_info',
    'fields',
}


@click.group()
@click.pass_context
def meta(ctx, **kwargs):
    """
    Read and update meta values for a dataset.
    """


@meta.command(name='get')
@click.option(
    "--output-format", "-o", type=click.Choice(["text", "json"]), default="text",
)
@click.option(
    "--json-style",
    type=click.Choice(["extracompact", "compact", "pretty"]),
    default="pretty",
    help="How to format the JSON output. Only used with -o json",
)
@click.argument('dataset')
@click.argument('keys', required=False, nargs=-1)
@click.pass_context
def meta_get(ctx, output_format, json_style, dataset, keys):
    """
    Prints the value of meta keys for the given dataset.
    """
    rs = RepositoryStructure(ctx.obj.repo)

    try:
        ds = rs[dataset]
    except KeyError:
        raise click.UsageError(f"No such dataset: {dataset}")

    if keys:
        items = {}
        missing_keys = []
        for key in keys:
            try:
                items[key] = ds.get_meta_item(key)
            except KeyError:
                missing_keys.append(key)

        if missing_keys:
            raise click.UsageError(
                f"Couldn't find items: {', '.join(sorted(missing_keys))}"
            )
    else:
        items = dict(ds.iter_meta_items())

    fp = resolve_output_path('-')
    if output_format == 'text':
        indent = '    '
        for key, value in items.items():
            click.secho(key, bold=True)
            serialized = format_json_for_output(value, fp, json_style=json_style)
            lines = serialized.splitlines()
            for i, line in enumerate(lines):
                fp.write(f"{indent}{line}\n")
    else:
        dump_json_output(items, fp, json_style=json_style)


class KeyValueType(click.ParamType):
    name = "key=value"

    def convert(self, value, param, ctx):
        value = tuple(value.split('=', 1))
        if len(value) != 2:
            self.fail(f"{value} should be of the form KEY=VALUE", param, ctx)

        key, value = value
        if not key:
            self.fail(f"Key should not be empty", param, ctx)

        return key, value


@meta.command(name='set')
@click.option(
    "--message",
    "-m",
    help="Use the given message as the commit message",
    type=StringFromFile(encoding="utf-8"),
)
@click.argument('dataset')
@click.argument(
    'items',
    type=KeyValueType(),
    required=True,
    nargs=-1,
    metavar='KEY=VALUE [KEY=VALUE...]',
)
@click.pass_context
def meta_set(ctx, message, dataset, items):
    """
    Prints the value of meta keys for the given dataset.
    """
    rs = RepositoryStructure(ctx.obj.repo)

    try:
        ds = rs[dataset]
    except KeyError:
        raise click.UsageError(f"No such dataset: {dataset}")

    if ds.version < 2:
        raise InvalidOperation(
            "This repo doesn't support meta changes, use `sno upgrade`"
        )

    if message is None:
        message = f'Update metadata for {dataset}'

    existing_meta_items = dict(ds.iter_meta_items())

    def _meta_change_dict(key, value):
        change = {
            '+': value,
        }
        if key in existing_meta_items:
            change['-'] = existing_meta_items[key]
        return change

    patch = {
        "sno.diff/v1+hexwkb": {
            dataset: {
                "meta": {key: _meta_change_dict(key, value) for (key, value) in items}
            }
        },
        "sno.patch/v1": {"message": message},
    }
    patch_file = io.StringIO()
    json.dump(patch, patch_file)
    patch_file.seek(0)
    apply_patch(
        repo=ctx.obj.repo, commit=True, patch_file=patch_file, allow_empty=False
    )
