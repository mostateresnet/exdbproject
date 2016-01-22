import argparse
import os
import re
import subprocess
import colorama
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.conf import settings


def confirm(string, default=False):
    yell_at = False
    while True:
        if yell_at:
            print("I didn't understand you. Please specify '(y)es' or '(n)o'.")

        print(string, '[Y/n]' if default else '[y/N]', end=' ')
        answer = input().strip().lower()

        if not answer:
            return default
        elif answer == 'y' or answer == 'n':
            return answer == 'y'
        else:
            yell_at = True


class Command(BaseCommand):
    help = 'Verify the code with tests and linting'
    allow_modification = False

    def test(self, *options):
        call_command('test', *options)

    def js_lint(self):
        files = self.find_files_by_ext('js', settings.JS_FILE_EXCLUDED_DIRS)
        subprocess.call(['jslint'] + files)

    def js_cs(self):
        files = self.find_files_by_ext('js', settings.JS_FILE_EXCLUDED_DIRS)

        warning = 'WARNING: jscs will modify javascript files WITHOUT confirmation!\nAre you sure that you want to proceed?'
        if self.allow_modification or confirm(warning):
            files = ['--fix'] + files
        subprocess.call(['jscs'] + files)

    def coverage(self):
        def color_report(report):
            # output report in a pretty way
            colorama.init()
            for line in report.split('\n'):
                match = re.match(r'^[^\s]+\s+\d+\s+\d+\s+(?P<total_coverage>\d+%)', line)
                if not match:
                    print(colorama.Style.RESET_ALL + line)
                elif match.groupdict()['total_coverage'] != '100%':
                    print(colorama.Fore.RED + line)
                else:
                    print(colorama.Fore.GREEN + line)

        source = 'exdb'
        omitted = '*migrations/*'
        # shell is true here to prevent an error apparently caused by not having a
        # shell and because it was easier to write
        subprocess.call('coverage run --source="%s" --omit="%s" manage.py test -c' % (source, omitted), shell=True)
        report = subprocess.check_output('coverage report'.split()).decode('utf-8')
        subprocess.call('coverage html --omit="%s"' % omitted, shell=True)

        match = re.search(r'TOTAL\s+\d+\s+\d+\s+(?P<total_coverage>\d+%)\s*', report)
        if not match:
            print(report)
            print("Report failure. Couldn't find total percentage.")
        elif match and match.groupdict()['total_coverage'] != '100%':
            color_report(report)
            print("Didn't pass coverage. See: file://%s" % os.path.abspath(os.path.join('htmlcov', 'index.html')))
        else:
            print("%s coverage." % match.groupdict()['total_coverage'])

    def pep8(self):
        warning = 'WARNING: autopep8 will modify python files WITHOUT confirmation!\nAre you sure that you want to proceed?'
        if self.allow_modification or confirm(warning):
            subprocess.call([
                'autopep8',         # the command
                '-i',               # change the files in place
                '-r',               # recurse through directories
                '--aggressive',     # enables non-whitespace changes
                '--max-line-length', '119',
                '--exclude', 'migrations,.git',
                '.',                # in the current directory
            ])

    def pylint(self):
        pylint_disable = ','.join(
            ('C0103',
             'C0111',
             'C0301',
             'C0302',
             'C0330',
             'E1101',
             'E1103',
             'I0011',
             'R0201',
             'R0901',
             'R0903',
             'R0904',
             'W0142',
             'W0201',
             'W0212',
             'W0221',
             'W0232',
             'W0611'))

        files_to_check = self.find_files_by_ext('py', settings.PY_FILE_EXCLUDED_DIRS)

        generated_members = ','.join(('REQUEST', 'acl_users', 'aq_parent', 'objects'))

        result = subprocess.call([
            'pylint',
            '-f', 'colorized',      # format, colorized
            '-r', 'n',              # full report, no
            '-d', pylint_disable,   # enable or diable codes
            '--generated-members=%s' % generated_members,
            '--dummy-variables-rgx=_|args|kwargs',  # variables which may or may not be used
        ] + files_to_check
        )

        if result == 0:
            print('Pylint was successful!')

    def find_files_by_ext(self, ext, exclude=None):
        exclude = exclude or []

        js_regex = re.compile(r'.*\.' + ext + '$')
        file_list = []
        for root, folders, files in os.walk('.'):
            folders[:] = [f for f in folders if f not in exclude]
            for filename in files:
                if js_regex.match(filename):
                    file_list.append(os.path.join(root, filename))
        return file_list

    def add_arguments(self, parser):
        parser.add_argument('-f', '--fix', action='store_true')
        parser.add_argument('subcommand', nargs='?')
        parser.add_argument('command-args', nargs=argparse.REMAINDER)

    def handle(self, *args, **options):
        if options.get('fix'):
            self.allow_modification = True

        subcommand = options['subcommand']
        # allow users to call individual methods with verify
        # it shouldn't be an issue that someone can call class methods if they like
        if subcommand and hasattr(self, subcommand) and hasattr(getattr(self, subcommand), '__call__'):
            getattr(self, subcommand)(*options['command-args'])
        else:
            self.js_cs()
            self.js_lint()
            # self.coverage handles both python and js coverage
            self.coverage()
            self.pep8()
            self.pylint()
