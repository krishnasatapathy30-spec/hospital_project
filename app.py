import importlib.util
import os

# Load the existing Flask app from the folder with a space in its name
base = os.path.dirname(__file__)
source_path = os.path.join(base, 'main folder', 'app.py')
spec = importlib.util.spec_from_file_location('hospital_main_app', source_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# Ensure the application's database and migrations are initialized when imported
try:
	_init = getattr(module, 'init_db', None)
	if callable(_init):
		_init()
except Exception:
	pass

# Expose the Flask application object as `app` for Gunicorn / Render
app = getattr(module, 'app')

# If the inner app's templates/static live in the 'main folder', ensure Flask knows their paths
inner_folder = os.path.join(base, 'main folder')
templates_dir = os.path.join(inner_folder, 'templates')
static_dir = os.path.join(inner_folder, 'static')
if os.path.isdir(templates_dir):
	try:
		app.template_folder = templates_dir
	except Exception:
		pass
if os.path.isdir(static_dir):
	try:
		app.static_folder = static_dir
	except Exception:
		pass
try:
	# set root_path to inner folder so resource loading uses correct base
	if os.path.isdir(inner_folder):
		app.root_path = inner_folder
except Exception:
	pass


if __name__ == '__main__':
	# convenience: allow `python app.py` to start the dev server for local testing
	try:
		_init = getattr(module, 'init_db', None)
		if callable(_init):
			_init()
	except Exception:
		pass
	app.run(debug=True)
