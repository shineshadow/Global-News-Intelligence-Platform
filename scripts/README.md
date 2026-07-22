## System Dependencies

### Debian/Ubuntu run script:

```bash
bash scripts/install-sys-deps.sh
```
### Or in terminal:

```bash
sudo apt update

sudo apt install -y \
    postgresql \
    postgresql-contrib \
    redis-server \
    curl \
    git \
    build-essential \
    libpq-dev
```    

### Your dependency layers would then look like this

```text
OS / Debian/Ubuntu packages
    ↓
sudo apt install
    ↓
scripts/install-sys-deps.sh

Python packages
    ↓
pyproject.toml

JavaScript packages
    ↓
package.json
```