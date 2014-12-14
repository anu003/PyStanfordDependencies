# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import subprocess
import tempfile
from .StanfordDependencies import StanfordDependencies
from .Token import Token

JAVA_CLASS_NAME = 'edu.stanford.nlp.trees.EnglishGrammaticalStructure'

class SubprocessBackend(StanfordDependencies):
    """Interface to Stanford Dependencies via subprocesses. This means
    that each call opens a pipe to Java. It has the advantage that
    it should work out of the box if you have Java but is slower than
    other backends. As such, convert_trees() will be more efficient than
    convert_tree() for this backend."""
    def __init__(self, jar_filename=None, download_if_missing=False,
                 version=None, java_command='java'):
        """The java_command flag is the path to a java binary."""
        StanfordDependencies.__init__(self, jar_filename, download_if_missing,
                                      version)
        self.java_command = java_command
    def convert_trees(self, ptb_trees, java='java', representation='basic',
                      include_punct=True, include_erased=False):
        """Convert a list of Penn Treebank formatted trees (ptb_trees)
        into Stanford Dependencies. The dependencies are represented
        as a list of sentences, where each sentence is itself a list of
        Token objects.

        Currently supported representations are 'basic', 'collapsed',
        'CCprocessed', and 'collapsedTree' which behave the same as they
        in the CoreNLP command line tools."""
        with tempfile.NamedTemporaryFile() as input_file:
            for ptb_tree in ptb_trees:
                input_file.write(ptb_tree + '\n')
            input_file.flush()

            command = [self.java_command, '-ea', '-cp', self.jar_filename,
                       JAVA_CLASS_NAME, '-' + representation, '-treeFile',
                       input_file.name, '-conllx']
            sd_process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE)
            stderr = sd_process.stderr.read()
            output = sd_process.stdout.read()
            if sd_process.wait():
                if 'Unsupported major.minor version' in stderr:
                    self.java_is_too_old()
                raise RuntimeError("Bad exit code from Stanford CoreNLP")

        current_sentence = []
        sentences = []
        def flush():
            if current_sentence:
                sentences.append(list(current_sentence))
                del current_sentence[:]
        for line in output.splitlines():
            line = line.strip()
            if line:
                token = Token.from_string(line)
                if token.deprel == 'erased' and not include_erased:
                    continue
                if token.deprel == 'punct' and not include_punct:
                    continue
                current_sentence.append(token)
            else:
                flush()
        flush()

        if len(sentences) != len(ptb_trees):
            raise RuntimeError("Only got %d sentences from Stanford Dependencies when given %d trees." % (len(sentences), len(ptb_trees)))
        return sentences
    def convert_tree(self, ptb_tree, **kwargs):
        """Converts a single Penn Treebank format tree to Stanford
        Dependencies. See convert_trees for more details."""
        return self.convert_trees([ptb_tree], **kwargs)[0]
