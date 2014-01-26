# fix broken locale
if not python -c 'import locale; locale.getdefaultlocale();' >/dev/null ^&1
    set -gx LANG en_US.UTF-8
    set -gx LC_ALL en_US.UTF-8
end

# set paths
set DIR (dirname (status -f))
set -gx PATH $PATH $DIR/../bin $DIR/../app
set -gx PYTHONPATH $PYTHONPATH $DIR/../app
