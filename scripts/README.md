# Manually installing this package

On the host machine, clone this repository, generate the .whl file and start a http server:

```bash
python3 -m venv venv
source venv/bin/activate
pip install wheel
pip install -e .
python3 -m build --wheel
python3 -m http.server
```

On the target, download the install script and wheel to `/tmp/`:
```bash
wget -O /tmp/install-packages.py <host IP>:8000/scripts/install-packages.py
wget -O /tmp/nuttx_periphery-0.1.0-py3-none-any.whl <host IP>:8000/dist/nuttx_periphery-0.1.0-py3-none-any.whl
```

Now run the installer (defaults: install to `/data`, use the newest `.whl` in the script directory):

```bash
python /tmp/install-packages.py /data /tmp/nuttx_periphery-0.1.0-py3-none-any.whl
```

The script and wheel must live in the same directory (e.g. `/tmp/`) unless the wheel path is passed explicitly.
