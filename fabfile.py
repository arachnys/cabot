from fabric.api import *
from fabric.contrib.files import *
from fabric.contrib.project import rsync_project
from subprocess import check_output


env.use_ssh_config = True

env.user = 'ubuntu'

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
HOME_DIR = '/home/ubuntu'
DEPLOY_PATH = '%s/cabot' % HOME_DIR
LOG_DIR = '/var/log/cabot/'
VENV_DIR = '%s/venv' % HOME_DIR
BACKUP_DIR = '/tmp/'

PG_DATABASE = 'index'
PG_USERNAME = 'cabot'
PG_PASSWORD = 'cabot'  # You should probably change this


def _ensure_dirs():
    dirs = [LOG_DIR]
    for d in dirs:
        sudo('mkdir -p {d}'.format(d=d))
        sudo('chmod -R 777 {d}'.format(d=d))


def _setup_venv():
    with settings(warn_only=True):
        if sudo('test -d %s' % VENV_DIR).failed:
            sudo('virtualenv %s' % VENV_DIR)


def install_requirements(deploy_path=DEPLOY_PATH):
    sudo("foreman run -e conf/{env}.env {venv}/bin/pip install --editable {path} --exists-action=w".format(
        env=env.deploy_version, venv=VENV_DIR, path=deploy_path))


def run_migrations(deploy_path=DEPLOY_PATH):
    with cd(deploy_path):
        with prefix("source {venv}/bin/activate".format(venv=VENV_DIR)):
            sudo(
                "foreman run -e conf/{env}.env python manage.py syncdb".format(env=env.deploy_version))
            sudo(
                "foreman run -e conf/{env}.env python manage.py migrate cabotapp --noinput".format(env=env.deploy_version))
            # Wrap in failure for legacy reasons
            # https://github.com/celery/django-celery/issues/149
            print "You can ignore an error message regarding 'relation \"celery_taskmeta\" already exists'"
            with settings(warn_only=True):
                sudo(
                    "foreman run -e conf/{env}.env python manage.py migrate djcelery --noinput".format(env=env.deploy_version))


def collect_static(deploy_path=DEPLOY_PATH):
    with cd(deploy_path):
        with prefix("source {venv}/bin/activate".format(venv=VENV_DIR)):
            sudo(
                "foreman run -e conf/{env}.env python manage.py collectstatic --noinput".format(env=env.deploy_version))
            sudo(
                "foreman run -e conf/{env}.env python manage.py compress".format(env=env.deploy_version))


def setup_upstart(deploy_path=DEPLOY_PATH):
    with cd(deploy_path):
        # Point at master (i.e. symlinked) path
        procfile = os.path.join(DEPLOY_PATH, 'Procfile')
        env_file = os.path.join(DEPLOY_PATH, 'conf', '%s.env' %
                                env.deploy_version)
        template_file = os.path.join(DEPLOY_PATH, 'upstart')
        sudo('foreman export upstart /etc/init -f {conf} -e {env} -u ubuntu -a cabot -t {tmplt}'.format(
            conf=procfile, env=env_file, tmplt=template_file))


def production():
    """
    Select production instance(s)
    """
    env.hosts = ['cabot.arachnys.com']


def restart():
    with settings(warn_only=True):
        if sudo('restart cabot').failed:
            sudo('start cabot')


def stop():
    with settings(warn_only=True):
        sudo('stop cabot')


def provision():
    """
    Provision a clean Ubuntu 12.04 instance with dependencies
    """
    with open(os.path.expanduser('~/.ssh/id_rsa.pub')) as f:
        local_ssh_key = f.read().strip('\n')
    put('bin/setup_dependencies.sh', '/tmp/setup_dependencies.sh')
    sudo('LOCAL_SSH_KEY="%s" bash /tmp/setup_dependencies.sh' % local_ssh_key)
    # Clean up
    run('rm /tmp/setup_dependencies.sh')


def deploy(deploy_version=None):
    """
      Deploy a new version of code to production or test server.

      Push code to remote server, install requirements, apply migrations,
      collect and compress static assets, export foreman to upstart,
      restart service
    """
    # TODO: replace this with
    # - zip up working directory
    # - upload and unzip into DEPLOY_PATH
    env.deploy_version = deploy_version or 'production'
    dirname = check_output(
        ["echo \"$(date +'%Y-%m-%d')-$(git log --pretty=format:'%h' -n 1)\""], shell=True).strip('\n ')
    deploy_path = os.path.join(HOME_DIR, dirname)
    run('mkdir -p {}'.format(deploy_path))
    print 'Uploading project to %s' % deploy_path
    rsync_project(
        remote_dir=deploy_path,
        local_dir='./',
        exclude=['.git', 'backups', 'venv',
                 'static/CACHE', '.vagrant', '*.pyc', 'dev.db'],
    )
    with cd(deploy_path):
        _ensure_dirs()
        _setup_venv()
        create_database()
        install_requirements(deploy_path)
        run_migrations(deploy_path)
        collect_static(deploy_path)
        # This may cause a bit of downtime
        run('ln -sfn {new} {current}'.format(
            new=deploy_path,
            current=DEPLOY_PATH
            ))
        setup_upstart(deploy_path)
    restart()
    print "Done!"


def backup():
    """
    Back up database locally

    TODO: send backups to s3
    """
    backup_file = 'outfile.sql.gz'
    with cd(BACKUP_DIR):
        run('PGPASSWORD={passwd} pg_dump -U {user} {database} | gzip > {backup}'.format(
            passwd=PG_PASSWORD,
            user=PG_USERNAME,
            database=PG_DATABASE,
            backup=backup_file
            ))
        get(backup_file, 'backups/%(basename)s')


def create_database():
    """Creates role and database"""
    with settings(warn_only=True):
        sudo(
            'psql -c "CREATE USER %s WITH NOCREATEDB NOCREATEUSER ENCRYPTED PASSWORD E\'%s\'"' %
            (PG_USERNAME, PG_PASSWORD), user='postgres')
        sudo('psql -c "CREATE DATABASE %s WITH OWNER %s"' %
             (PG_DATABASE, PG_USERNAME), user='postgres')


@parallel
def logs():
    """
    Tail logfiles
    """
    sudo('tail -f {logdir}* /var/log/nginx/*.log'.format(logdir=LOG_DIR))
