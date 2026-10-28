# Guía rápida de git para la tesina

Comandos para copiar y pegar en la terminal (en VS Code: **Terminal → New Terminal**), dentro de la carpeta del repo.

**La regla:** nunca se trabaja directo en `main`. Cada tarea va en su propia rama y, al terminar, entra a `main` por un *Pull Request* en GitHub.

En todos los comandos, cambia `atenea/nombre-de-la-tarea` por el nombre de tu tarea, sin espacios ni acentos. Por ejemplo: `atenea/marco-teorico`, `atenea/estado-del-arte`.

---

## 1. Empezar una tarea nueva

Trae lo último de `main` y crea tu rama:

```bash
git checkout main
git pull
git checkout -b atenea/nombre-de-la-tarea
```

Desde aquí, todo lo que hagas queda en tu rama.

## 2. Guardar tu avance

Hazlo cada vez que termines una parte. Mejor seguido que todo al final.

```bash
git status
git add .
git commit -m "docs: describe en pocas palabras qué hiciste"
```

`git status` te muestra qué archivos cambiaste. Revisa que sean los tuyos antes de seguir.

## 3. Subir tu rama a GitHub

**La primera vez** que subes esta rama:

```bash
git push -u origin atenea/nombre-de-la-tarea
```

**Las siguientes veces**, basta con:

```bash
git push
```

## 4. Seguir trabajando otro día

Vuelve a tu rama y trae lo que hayas subido desde otra computadora:

```bash
git checkout atenea/nombre-de-la-tarea
git pull
```

## 5. Traer a tu rama lo nuevo de `main`

Úsalo si Arturo fusionó cambios en `main` mientras trabajabas y los necesitas:

```bash
git checkout atenea/nombre-de-la-tarea
git pull --no-rebase --no-edit origin main
```

Si aparece la palabra **CONFLICT**, no sigas: corre el siguiente comando y avísale a Arturo.

```bash
git merge --abort
```

## 6. Terminar la tarea: Pull Request

1. Sube tu último avance (pasos 2 y 3).
2. Abre https://github.com/Devloiza/TT. Aparece un botón verde **"Compare & pull request"** para tu rama; dale clic.
   - Si no aparece, ve a **Pull requests → New pull request** y elige tu rama en el segundo recuadro, el de la derecha.
3. Escribe un título corto (qué hiciste) y da clic en **"Create pull request"**.
4. Avísale a Arturo para que lo revise y lo fusione.

## 7. Después de que se fusiona tu Pull Request

Regresa a `main`, tráelo actualizado y borra la rama que ya terminó:

```bash
git checkout main
git pull
git branch -d atenea/nombre-de-la-tarea
```

Para la siguiente tarea, vuelve al paso 1.

---

## ¿En qué rama estoy?

```bash
git branch
```

La rama actual es la que tiene el asterisco `*`.

## Si algo sale mal

| Mensaje o situación | Qué hacer |
|:--|:--|
| Al hacer `git push` sale **"rejected"** | Corre `git pull --no-rebase --no-edit` y luego `git push`. Si sale **CONFLICT**, corre `git merge --abort` y avísale a Arturo. |
| Al hacer `git pull` sale **"divergent branches"** | Usa `git pull --no-rebase --no-edit`, que es la misma operación sin ese error. |
| Al borrar la rama (paso 7) sale **"not fully merged"** | Confirma en GitHub que tu Pull Request dice **Merged**. Si es así, corre `git branch -D atenea/nombre-de-la-tarea`, con **D** mayúscula. |
| Se abrió un editor raro en la terminal (letras `~` a la izquierda) | Escribe `:q!` y presiona Enter para salir. Luego avísale a Arturo. |
| Al cambiar de rama sale **"Your local changes would be overwritten"** | Guarda tu avance primero (paso 2) y vuelve a intentar. |
| Escribiste en `main` sin querer y **todavía no** haces commit | Corre `git checkout -b atenea/nombre-de-la-tarea`: tus cambios se pasan a la rama nueva. |
| Escribiste en `main` sin querer y **ya** hiciste commit | No hagas push. Avísale a Arturo. |
| Cualquier otra cosa rara | No borres nada ni intentes "forzar" nada. Copia el mensaje y avísale a Arturo. |

## Lo que nunca hay que hacer

- `git push --force`: puede borrar el trabajo de la otra persona.
- Trabajar o hacer commit directo en `main`.

---

## Solo si usas una computadora nueva

Descarga el repo:

```bash
git clone https://github.com/Devloiza/TT.git
cd TT
```

Configura tu nombre y correo (se hace una sola vez por computadora):

```bash
git config --global user.name "Atenea Jimenez"
git config --global user.email "ateneajimenezjimenez@gmail.com"
```
