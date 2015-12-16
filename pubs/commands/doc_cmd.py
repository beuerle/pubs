import os
import subprocess

from .. import repo
from .. import color
from ..uis import get_ui
from .. import content
from ..utils import resolve_citekey, resolve_citekey_list

# doc --+- add $file $key [[-L|--link] | [-M|--move]] [-f|--force]
#       +- remove $key [$key [...]] [-f|--force]
#       +- export $key [$path]
#       +- open $key [-w|--with $cmd]
# supplements attach, open

def parser(subparsers):
    doc_parser = subparsers.add_parser('doc', help='manage the document relating to a publication')
    doc_subparsers = doc_parser.add_subparsers(title='document actions', help='actions to interact with the documents',
                                               dest='action')

    add_parser = doc_subparsers.add_parser('add', help='add a document to a publication')
    add_parser.add_argument('-f', '--force', action='store_true', dest='force', default=False,
                           help='force overwriting an already assigned document')
    add_parser.add_argument('document', nargs=1, help='document file to assign')
    add_parser.add_argument('citekey', nargs=1, help='citekey of the publication')
    add_exclusives = add_parser.add_mutually_exclusive_group()
    add_exclusives.add_argument('-L', '--link', action='store_false', dest='link', default=False,
                           help='do not copy document files, just create a link')
    add_exclusives.add_argument('-M', '--move', action='store_true', dest='move', default=False,
                           help='move document instead of of copying (ignored if --link)')

    remove_parser = doc_subparsers.add_parser('remove', help='remove assigned documents from publications')
    remove_parser.add_argument('citekeys', nargs='+', help='citekeys of the publications')
    remove_parser.add_argument('-f', '--force', action='store_true', dest='force', default=False,
                              help='force removing assigned documents')

    # favor key+ path  over:  key
    export_parser = doc_subparsers.add_parser('export', help='export assigned documents to given path')
    export_parser.add_argument('citekeys', nargs='+', help='citekeys of the documents to export')
    export_parser.add_argument('path', nargs=1, help='directory to export the files to')

    open_parser = doc_subparsers.add_parser('open', help='open an assigned document')
    open_parser.add_argument('citekey', nargs=1, help='citekey of the document to open')
    open_parser.add_argument('-w', '--with', dest='cmd', help='command to open the file with')

    return doc_parser

def command(conf, args):

    ui = get_ui()
    rp = repo.Repository(conf)


    # print(args)
    # ui.exit()

    if args.action == 'add':
        citekey = resolve_citekey(rp, args.citekey[0], ui=ui, exit_on_fail=True)
        paper = rp.pull_paper(citekey)

        if paper.docpath is not None and not args.force:
            msg = ("The publication {} has already the document {} assigned." + os.linesep +
               "Overwrite? ").format(color.dye_out(paper.citekey, 'citekey'), color.dye_out(paper.docpath, 'filepath'))
            if not ui.input_yn(question=msg, default='n'):
                ui.exit(0)
            else:
                try:
                    rp.remove_doc(paper.citekey)
                except (ValueError, IOError) as v:
                    ui.error(v.message)
                    ui.exit(1)

        try:
            document = args.document[0]
            if args.link:
                rp.push_doc(paper.citekey, document, copy=False)
            else:
                rp.push_doc(paper.citekey, document, copy=True)
            if not args.link and args.move:
                content.remove_file(document)

            ui.message('{} added to {}'.format(color.dye_out(document, 'filepath'),
                                                  color.dye_out(paper.citekey, 'citekey')))
        except (ValueError, IOError) as v:
            ui.error(v.message)
            ui.exit(1)

    elif args.action == 'remove':

        for key in resolve_citekey_list(rp, args.citekeys, ui=ui, exit_on_fail=True):
            paper = rp.pull_paper(key)

            # if there is no document (and the user cares) -> inform + continue
            if paper.docpath is None and not args.force:
                ui.message('Publication {} has no assigned document. Not removed.'.format(
                    color.dye_out(paper.citekey, 'citekey')))
                continue

            if not args.force:
                msg = 'Do you really want to remove {} from {} ?'.format(color.dye_out(paper.docpath, 'filepath'),
                                                                         color.dye_out(paper.citekey, 'citekey'))
                if not ui.input_yn(question=msg, default='n'):
                    continue

            try:
                rp.remove_doc(paper.citekey)
            except (ValueError, IOError) as v:
                ui.error(v.message)
                ui.exit(1)

    elif args.action == 'export':

        if os.path.isdir(args.path[0]):
            path = args.path[0]
            if not path.endswith('/'):
                path += '/'
        else:
            ui.error('{} is not a directory. Quit.'.format(
                color.dye_err(args.path[0], 'filepath')))
            ui.exit(1)

        for key in resolve_citekey_list(rp, args.citekeys, ui=ui, exit_on_fail=True):
            try:
                paper = rp.pull_paper(key)
                doc = paper.docpath

                if doc is None:
                    ui.message('Publication {} has no document assigned.'.format(
                        color.dye_out(paper.citekey, 'citekey')))
                else:
                    real_doc_path = rp.pull_docpath(key)
                    dest_path = path + os.path.basename(real_doc_path)
                    content.copy_content(real_doc_path, dest_path)
            except (ValueError, IOError) as e:
                ui.error(e.message)

    elif args.action == 'open':
        with_command = args.cmd
        citekey = resolve_citekey(rp, args.citekey[0], ui=ui, exit_on_fail=True)
        paper = rp.pull_paper(citekey)

        if paper.docpath is None:
            ui.error('No document associated with the entry {}. Quit.'.format(
                      color.dye_err(citekey, 'citekey')))
            ui.exit()

        if with_command is None:
            with_command = conf['main']['open_cmd']
        if with_command is None: # default in conf have not been changed
            pass # TODO platform specific

        try:
            docpath = content.system_path(rp.databroker.real_docpath(paper.docpath))
            cmd = with_command.split()
            cmd.append(docpath)
            subprocess.Popen(cmd)
            ui.message('{} opened.'.format(color.dye_out(docpath, 'filepath')))
        except OSError:
            ui.error("Command does not exist: %s." % with_command)
            ui.exit(127)
