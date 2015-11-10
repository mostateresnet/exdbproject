from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
import os
import re
import subprocess
import argparse

class Command(BaseCommand):
    help = 'Closes the specified poll for voting'
    allow_modification = False

    def test(self, options):
        call_command('test', *options)

    def js_lint(self):
        files = self.find_js_files()
        process = subprocess.call(['jslint'] + files)

    def js_cs(self):
        files = self.find_js_files()
        if self.allow_modification:
            files = ['--fix'] + files
        process = subprocess.call(['jscs'] + files)

    def find_js_files(self):
        js_regex = re.compile(r'.*\.js$')
        file_list = []
        for root, folders, files in os.walk('.'):
            for filename in files:
                if js_regex.match(filename):
                    file_list.append(os.path.join(root, filename))
        return file_list

    def add_arguments(self, parser):
        parser.add_argument('fix', nargs='?')
        parser.add_argument('subcommand', nargs='?')
        parser.add_argument('command-args', nargs=argparse.REMAINDER)

    def handle(self, *args, **options):
        if options.get('fix'):
            self.allow_modification = True

        subcommand = options['subcommand']
        # it shouldn't be an issue that someone can call class methods if they like
        if subcommand and hasattr(self, subcommand) and hasattr(getattr(self, subcommand), '__call__'):
            getattr(self, subcommand)(options['command-args'])
        else:
            self.js_cs()
            self.js_lint()
            self.test([])

