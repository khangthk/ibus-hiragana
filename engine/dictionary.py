# -*- coding: utf-8 -*-
#
# ibus-replace-with-kanji - Replace with Kanji Japanese input method for IBus
#
# Copyright (c) 2017 Esrille Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import logging
import re

logger = logging.getLogger(__name__)

_re_not_yomi = re.compile(r'[^ぁ-ゖァ-ー―]')

class Dictionary:

    def __init__(self, path):
        logger.info("Dictionary(%s)", path)

        self.__dict_base = {}
        self.__dict = {}

        self.__yomi = ''
        self.__no = 0
        self.__cand = []
        self.__dirty = False

        self.__orders_path = ''

        # Load Katakana dictionary first so that Katakana words come after Kanji words.
        katakana_path = os.path.join(os.getenv('IBUS_REPLACE_WITH_KANJI_LOCATION'), 'katakana.dic')
        self.__load_dict(self.__dict_base, katakana_path);

        # Load system dictionary
        self.__load_dict(self.__dict_base, path);

        # Load private dictionary
        self.__dict = self.__dict_base.copy()

        my_path = os.path.expanduser('~/.local/share/ibus-replace-with-kanji/my.dic')
        self.__load_dict(self.__dict, my_path, 'a+');

        base = os.path.basename(path)
        if base:
            self.__orders_path = os.path.expanduser('~/.local/share/ibus-replace-with-kanji')
            self.__orders_path = os.path.join(self.__orders_path, base)
            self.__load_dict(self.__dict, self.__orders_path, 'a+');

    def __load_dict(self, dict, path, mode='r'):
        with open(path, mode) as file:
            file.seek(0, 0)
            for line in file:
                line = line.strip(' \n/')
                if not line or line[0] == ';':
                    continue;
                p = line.split(' ', 1)
                yomi = p[0]
                cand = p[1].strip(' \n/').split('/')
                if not yomi in dict:
                    dict[yomi] = cand
                else:
                    update = list(dict[yomi])
                    for i in reversed(cand):
                        if i in update:
                            update.remove(i)
                        update.insert(0, i)
                    dict[yomi] = update
            logger.info("Loaded %s", path)

    def __str(self, s):
        if s[-1] == '―':
            return s[:-1]
        return s

    def reset(self):
        self.__yomi = ''

    def next(self):
        if self.__no + 1 < len(self.__cand):
            self.__no += 1
        return self.__str(self.__cand[self.__no]);

    def previous(self):
        if 0 < self.__no:
            self.__no -= 1
        return self.__str(self.__cand[self.__no]);

    def current(self):
        if self.__yomi:
            return self.__str(self.__cand[self.__no]);
        return ''

    def set_current(self, index):
        index = int(index)
        if self.__yomi and 0 <= index and index < len(self.__cand):
            self.__no = index;

    def reading(self):
        return self.__yomi

    def cand(self):
        if self.__yomi:
            return self.__cand;
        return []

    def lookup(self, yomi):
        self.reset()
        size = len(yomi)
        for i in range(size - 1, -1, -1):
            y = yomi[i:size]
            if _re_not_yomi.search(y):
                break;
            if y in self.__dict:
                self.__yomi = y
                self.__cand = self.__dict[y]
                self.__no = 0
        return self.current()

    def confirm(self):
        if not self.__yomi or self.__no == 0:
            return
        # Update the order of the candidates.
        cand = self.__cand[:]
        last = cand[self.__no]
        cand.remove(last)
        cand.insert(0, last)
        self.__dict[self.__yomi] = cand
        self.__dirty = True;

    def save_orders(self):
        if not self.__dirty:
            return
        with open(self.__orders_path, 'w') as file:
            for yomi, cand in self.__dict.items():
                if not yomi in self.__dict_base or cand != self.__dict_base[yomi]:
                    file.write(yomi + " /" + '/'.join(cand) + "/\n")
        self.__dirty = False

    def dump(self):
        print('\'', self.__yomi, '\' ', self.__no, ' ', self.__cand, sep='')
