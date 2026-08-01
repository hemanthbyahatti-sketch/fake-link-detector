import marshal, pathlib, dis
root = pathlib.Path(__file__).resolve().parent
for name in ['app', 'fake']:
    path = root / '__pycache__' / f'{name}.cpython-314.pyc'
    print(f'=== {name} ===')
    if not path.exists():
        print('missing', path)
        continue
    data = path.read_bytes()
    code = marshal.loads(data[16:])
    print('module:', code.co_name)
    print('names:', code.co_names)
    print('consts:', code.co_consts[:20])
    print('firstlineno:', code.co_firstlineno)
    print('--- disassembly ---')
    dis.dis(code)
    print()
