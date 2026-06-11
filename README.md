# loops_opencode

Runner para ejecutar objetivos largos en opencode usando sesiones nuevas y estado persistente.

## Qué incluye

- `commands/loop.md`: comando `/loop` para opencode.
- `scripts/opencode_loop_runner.py`: runner que ejecuta `/loop` en sesiones nuevas hasta que el estado quede `complete`.
- `scripts/run_opencode_loop.sh`: wrapper que activa `./venv` y ejecuta el runner.

## Instalación

Copiar el comando a la configuración de opencode:

```bash
mkdir -p ~/.config/opencode/commands
cp commands/loop.md ~/.config/opencode/commands/loop.md
```

Copiar los scripts al proyecto donde se va a usar el loop:

```bash
mkdir -p scripts
cp scripts/opencode_loop_runner.py scripts/run_opencode_loop.sh ./scripts/
chmod +x scripts/opencode_loop_runner.py scripts/run_opencode_loop.sh
```

El wrapper espera un entorno virtual local en `./venv`. Si preferís no usar wrapper:

```bash
python3 scripts/opencode_loop_runner.py "objetivo largo"
```

## Uso

Ejecutar un objetivo largo:

```bash
./scripts/run_opencode_loop.sh "objetivo largo"
```

Continuar un loop existente:

```bash
./scripts/run_opencode_loop.sh --continue
```

Limitar iteraciones:

```bash
./scripts/run_opencode_loop.sh --max-iterations 10 "objetivo largo"
```

Probar sin iniciar sesiones:

```bash
./scripts/run_opencode_loop.sh --dry-run --max-iterations 2 "probar runner"
```

## MCPs y Skills

Permitir solo ciertos MCPs y Skills:

```bash
./scripts/run_opencode_loop.sh --mcp web_search --skill research-sourcing "objetivo largo"
```

Permitir varios:

```bash
./scripts/run_opencode_loop.sh --mcp web_search,playwright --skill research-sourcing --skill research-synthesis "objetivo largo"
```

Deshabilitar MCPs y Skills:

```bash
./scripts/run_opencode_loop.sh --no-mcp --no-skills "objetivo local"
```

Continuar manteniendo la selección:

```bash
./scripts/run_opencode_loop.sh --continue --mcp web_search --skill research-sourcing
```

## Estado persistente

El loop usa:

```text
.opencode/loop/state.md
.opencode/loop/learned.md
.opencode/loop/runs/
```

El runner termina cuando `state.md` contiene:

```text
status: complete
```

## Notas

- Cada iteración usa `opencode run --command loop`, lo que crea una sesión nueva cuando no se pasa `--continue` ni `--session` a opencode.
- La continuidad vive en `.opencode/loop/`, no en el contexto conversacional.
- La selección de MCPs/Skills se aplica por protocolo del comando `/loop`; opencode CLI no expone flags nativos `--mcp` o `--skill`.
