# Dev Command Backend

`commands/dev` is the internal command backend used by `pi-odoo-devkit.sh`.

For normal usage, prefer the main entrypoint:

```bash
./pi-odoo-devkit.sh --help
```

From an Odoo project repo, you can also use the linked helper:

```bash
./.pi/tools/devkit --help
```

Useful commands:

- `./.pi/tools/devkit components` (shows available/unavailable skills with reasons)
- `./.pi/tools/devkit doctor`
- `./.pi/tools/devkit enable-skill <name>`
- `./.pi/tools/devkit disable-skill <name>`
- `./.pi/tools/devkit enable-command <name>`
- `./.pi/tools/devkit disable-command <name>`
- `./.pi/tools/devkit new-skill <skill-name>`
