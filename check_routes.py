from backend.main import app
for route in app.routes:
    methods = getattr(route, "methods", None)
    path = getattr(route, "path", None)
    name = getattr(route, "name", None)
    print(f"Path: {path} | Name: {name} | Methods: {methods} | Type: {type(route)}")
