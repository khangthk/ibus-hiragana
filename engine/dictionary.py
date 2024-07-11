# ibus-hiragana - Hiragana IME for IBus
#
# Copyright (c) 2017-2024 Esrille Inc.
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

from __future__ import annotations

import logging
import os
import re

import package

LOGGER = logging.getLogger(__name__)

DICTIONARY_VERSION = 'v1.0.0'
NON_YOMIGANA = re.compile(r'[^ぁ-ゖァ-ー―]')
YOMIGANA = re.compile(r'^[ぁ-ゖァ-ー―]+[、。，．]?$')
HIRAGANA = ('あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん'
            'がぎぐげござじずぜぞだぢづでどばびぶべぼぁぃぅぇぉゃゅょっぱぴぷぺぽゔ')
TYOUON = ('あいうえおあいうえおあいうえおあいうえおあいうえおあいうえおあいうえおあうおあいうえおあおん'
          'あいうえおあいうえおあいうえおあいうえおあいうえおあうおうあいうえおう')
OKURIGANA = re.compile(r'[ぁ-ゖ1iIkKgsStnbmrwW235]+$')
KATUYOU = {
    '1': ('', 'る', 'れば', 'ろ', 'よう', 'て', 'た', 'な', 'た', 'ま', 'ず', None, None),
    'i': ('く', 'い', 'ければ', None, 'かろう', 'くて', 'かった', None, None, None, None, None, None, '',
          'さ', 'み', 'げ', 'そう'),
    'I': ('く', 'い', 'ければ', None, 'かろう', 'くて', 'かった', None, None, None, None, None, None, '',
          'さ', 'み', 'げ', 'そう', 'な'),   # 小さい, 大きい
    'k': ('き', 'く', 'けば', 'け', 'こう', 'いて', 'いた', 'かな', 'きた', 'きま', 'かず', 'かせ', 'かれ'),
    'K': ('き', 'く', 'けば', 'け', 'こう', 'って', 'った', 'かな', 'きた', 'きま', 'かず', 'かせ', 'かれ'),  # 行く
    'g': ('ぎ', 'ぐ', 'げば', 'げ', 'ごう', 'いで', 'いだ', 'がな', 'ぎた', 'ぎま', 'がず', 'がせ', 'がれ'),
    's': ('し', 'す', 'せば', 'せ', 'そう', 'して', 'した', 'さな', 'した', 'しま', 'さず', 'させ', 'され'),
    'S': ('し', 'する', 'すれば', 'しろ', 'しよう', 'して', 'した', 'しな', 'した', 'しま', 'せず', 'させ', 'され'),  # 欲S
    't': ('ち', 'つ', 'てば', 'て', 'とう', 'って', 'った', 'たな', 'ちた', 'ちま', 'たず', 'たせ', 'たれ'),
    'n': ('に', 'ぬ', 'ねば', 'ね', 'のう', 'んで', 'んだ', 'なな', 'にた', 'にま', 'なず', 'なせ', 'なれ'),
    'b': ('び', 'ぶ', 'べば', 'べ', 'ぼう', 'んで', 'んだ', 'ばな', 'びた', 'びま', 'ばず', 'ばせ', 'ばれ'),
    'm': ('み', 'む', 'めば', 'め', 'もう', 'んで', 'んだ', 'まな', 'みた', 'みま', 'まず', 'ませ', 'まれ'),
    'r': ('り', 'る', 'れば', 'れ', 'ろう', 'って', 'った', 'らな', 'りた', 'りま', 'らず', 'らせ', 'られ'),
    'w': ('い', 'う', 'えば', 'え', 'おう', 'って', 'った', 'わな', 'いた', 'いま', 'わず', 'わせ', 'われ'),
    'W': ('い', 'う', 'えば', 'え', 'おう', 'うて', 'うた', 'わな', 'いた', 'いま', 'わず', 'わせ', 'われ'),  # 問う, 請う, 乞う, etc.
    '2': ('', None, None, None, None, 'て', 'た', None, 'た', 'ま', None, None, None),  # きて
    '3': (None, 'る', 'れば', None, None, None, None, None, None, None, None, None, None),  # くる
    '5': (None, None, None, 'い', 'よう', None, None, 'な', None, None, 'ず', 'させ', 'られ'),  # こい
}
DAKUON = 'がぎぐげござじずぜぞだぢづでどばびぶべぼ'
SEION = 'かきくけこさしすせそたちつてとはひふへほ'


class Dictionary:

    @staticmethod
    def opt_len(x):
        return 0 if x is None else len(x)

    # Compare okuri and yomi ignoring the Dakuten of the last character
    @staticmethod
    def strdcmp(okuri, yomi):
        assert 0 < len(yomi)
        last = len(yomi) - 1
        pos = DAKUON.find(okuri[last])
        if 0 <= pos:
            okuri = okuri[:last] + SEION[pos]
            if okuri == yomi:
                return True
        return False

    @staticmethod
    def strcmp(okuri, yomi):
        return okuri == yomi

    def __init__(self, system: str, user: str,
                 clear_history: bool = False,
                 permissible: bool = False):
        LOGGER.debug(f'Dictionary("{system}", "{user}", {clear_history}, {permissible})')

        self._dict_base = {}
        self._dict = {}

        self._yomi = ''
        self._no = 0
        self._cand = []
        self._order = []
        self._completed = []
        self._numeric = ''
        self._dirty = False
        self._strdcmp = self.strcmp

        self._orders_path = ''

        dir_path = os.path.join(package.get_datadir(), 'dic')

        try:
            # Load Katakana dictionary first so that Katakana words come after Kanji words.
            path = os.path.join(dir_path, 'katakana.dic')
            self._load_dict(self._dict_base, path)
        except OSError:
            LOGGER.exception('Could not load "katakana.dic"')

        if permissible and system == 'restrained.9.dic':
            try:
                path = os.path.join(dir_path, 'permissible.dic')
                self._load_dict(self._dict_base, path)
            except OSError:
                LOGGER.exception('Could not load "permissible.dic"')

        try:
            # Load system dictionary
            path = os.path.join(dir_path, system)
            self._load_dict(self._dict_base, path)
        except OSError:
            LOGGER.exception(f'Could not load "{path}"')

        # Load user dictionary
        self._dict = self._dict_base.copy()
        if user:
            path = os.path.join(package.get_user_datadir(), user)
            if os.path.abspath(path) == path:
                try:
                    self._load_dict(self._dict, path, 'a+')
                except OSError:
                    LOGGER.exception(f'Could not load "{path}"')

        # Load input history
        self._orders_path = os.path.join(package.get_user_datadir(), 'dic', system)
        try:
            if clear_history:
                LOGGER.debug('clear_history')
                with open(self._orders_path, 'w') as f:
                    f.write('; ' + DICTIONARY_VERSION + '\n')
            else:
                self._load_dict(self._dict, self._orders_path, 'a+', version_checked=False)
        except OSError:
            LOGGER.exception(f'Could not load "{self._orders_path}"')

    def _load_dict(self, dic: dict[str, list[str]], path: str, mode='r', version_checked=True):
        reorder_only = not version_checked
        try:
            with open(path, mode) as f:
                f.seek(0, 0)   # in case opened in the 'a+' mode
                for line in f:
                    line = line.strip(' \n/')
                    if not line:
                        continue
                    if line[0] == ';':
                        if line == '; ' + DICTIONARY_VERSION:
                            version_checked = True
                        continue
                    if not version_checked:
                        continue
                    p = line.split(' ', 1)
                    yomi = p[0]
                    cand = p[1].strip(' \n/').split('/')
                    # TODO: Check yomi is valid
                    if yomi.startswith('-'):
                        self._remove_entry(dic, yomi[1:], cand)
                    else:
                        self._merge_entry(dic, yomi, cand, reorder_only)
                        if yomi.endswith('―'):
                            self._merge_entry(dic, yomi[:-1], [yomi], reorder_only)
                LOGGER.debug(f'Loaded {path}')
        except OSError:
            LOGGER.exception(f'could not load "{path}"')

    def _merge_entry(self, dic: dict[str, list[str]], yomi: str, cand: list[str], reorder_only: bool):
        if yomi in cand:
            LOGGER.warning(f'unexpected candidate for "{yomi}": {cand}')
            cand.remove(yomi)
        if yomi not in dic:
            if not reorder_only:
                dic[yomi] = cand
            else:
                self._dirty = True
        else:
            update = dic[yomi][:]
            yougen = []
            for i in reversed(cand):
                if i in update:
                    update.remove(i)
                    update.insert(0, i)
                elif not reorder_only or i[0] in HIRAGANA or i[0] == '#':
                    if i[-1] == '―':
                        yougen.insert(0, i)
                    else:
                        update.insert(0, i)
                else:
                    self._dirty = True
            update.extend(yougen)   # extend() does not return anything
            dic[yomi] = update

    def _remove_entry(self, dic: dict[str, list[str]], yomi: str, cand: list[str]):
        if yomi not in dic:
            return
        update = [x for x in dic[yomi] if x not in cand]
        LOGGER.debug(f'_remove_entry: {dic[yomi]}→{update}')
        if update:
            dic[yomi] = update
        else:
            del dic[yomi]

    def reset(self):
        self._yomi = ''

    def set_current_to_next(self):
        if self._no + 1 < len(self._cand):
            self._no += 1
        return self._cand[self._no]

    def set_current_to_previous(self):
        if 0 < self._no:
            self._no -= 1
        return self._cand[self._no]

    def current(self):
        if self._yomi:
            return self._cand[self._no]
        return ''

    def set_current(self, index):
        index = int(index)
        if self._yomi and 0 <= index < len(self._cand):
            self._no = index

    def reading(self):
        return self._yomi

    def cand(self):
        if self._yomi:
            return self._cand
        return []

    # -1: yomi is not valid
    # 0: yomi can be valid; still missing a few letters
    # 1: yomi is valid
    def _match(self, okuri, yomi):
        if okuri and 0 <= '1iIkKgsStnbmrwW235'.find(okuri[-1]):
            suffix = okuri[-1]
            okuri = okuri[:-1]
        else:
            suffix = ''
        pos = min(len(okuri), len(yomi))

        # Check the fixed part of Okurigana
        if okuri:
            if yomi[:pos] == okuri[:pos]:
                if pos == len(okuri):
                    if not suffix:
                        return 1 if len(okuri) < len(yomi) else 0
                else:
                    return 0
            elif len(okuri) < len(yomi):
                return -1
            elif self._strdcmp(okuri, yomi):
                return 0
            else:
                return -1

        if not suffix or suffix not in KATUYOU:
            return -1

        # Check conjugations
        assert pos == len(okuri)
        yomi = yomi[pos:]
        if not yomi:
            return 0
        katuyou = KATUYOU[suffix]
        conj_len = len(max(katuyou, key=self.opt_len))
        for i in range(min(len(yomi), conj_len), 0, -1):
            for k in katuyou:
                if k is None or len(k) <= i:
                    continue
                if len(yomi) < len(k) and (k[:i] == yomi[:i] or self._strdcmp(k[:i], yomi[:i])):
                    return 0
            for k in katuyou:
                if k is None or len(k) != i:
                    continue
                if k == yomi[:i]:
                    return 1 if i < len(yomi) else 0
                elif len(yomi) == len(k) and self._strdcmp(k, yomi[:i]):
                    return 0

        # cf. 食べ
        if '' in katuyou:
            return 1 if 0 < len(yomi) else 0

        return -1

    def lookup(self, yomi, pos, anchor=0):
        LOGGER.debug(f'lookup({yomi}, {pos}, {anchor})')

        self.reset()
        # Look for the nearest hyphen.
        suffix = anchor + yomi[anchor:pos].rfind('―')
        if 0 <= suffix and not YOMIGANA.match(yomi[suffix:pos]):
            suffix = -1
        if suffix <= 0:
            numeric = ''
            has_numeric = False
            size = pos
            for i in range(size - 1, anchor - 1, -1):
                if not has_numeric and yomi[i].isnumeric():
                    numeric = yomi[i] + numeric
                    if 0 < i and yomi[i - 1].isnumeric():
                        continue
                    has_numeric = True
                elif NON_YOMIGANA.match(yomi[i]):
                    break
                y = yomi[i:size]
                if not has_numeric:
                    if y in self._dict:
                        self._yomi = y
                        self._cand = self._dict[y]
                        self._no = 0
                        self._order = []
                        self._completed = []
                        self._numeric = ''
                        LOGGER.debug(f'  yomi: "{self._yomi}", cand: {self._cand}')
                else:
                    yy = y.replace(numeric, '#')
                    if yy in self._dict:
                        if yy[1:] == self._yomi:
                            cand = self._cand[:]
                        else:
                            self._yomi = yy[1:]
                            cand = []
                        for c in reversed(self._dict[yy]):
                            item = c[1:]
                            if item in cand:
                                cand.remove(item)
                            cand.insert(0, item)
                        self._cand = cand
                        self._no = 0
                        self._order = []
                        self._completed = []
                        self._numeric = numeric
            return self.current()

        # Process suffix
        size = suffix + 1
        y = yomi
        for i in range(len(yomi[size:])):
            if NON_YOMIGANA.match(yomi[size + i]):
                y = y[:size + i]
                break
        for i in range(size - 2, anchor - 1, -1):
            if NON_YOMIGANA.match(y[i]):
                break
            if y[i:size] in self._dict:
                cand = ([], [])
                order = ([], [])
                for n, c in enumerate(self._dict[y[i:size]]):
                    pattern = OKURIGANA.search(c)
                    if pattern:
                        pos_okuri = pattern.start()
                    else:
                        pos_okuri = len(c)
                    okuri = c[pos_okuri:]
                    p = self._match(okuri, y[size:])
                    LOGGER.debug(f'lookup: {c} {y[size:]} => {p}')
                    c = c[:pos_okuri] + yomi[size:pos]
                    if 0 <= p:
                        assert p in (0, 1)
                        if c not in cand[p]:
                            cand[p].append(c)
                            order[p].append(n)
                if cand[0] or cand[1]:
                    for c in cand[0]:
                        if c in cand[1]:
                            at = cand[1].index(c)
                            del cand[1][at]
                            del order[1][at]
                    self._yomi = yomi[i:pos]
                    self._cand = cand[0] + cand[1]
                    self._no = 0
                    self._order = order[0] + order[1]
                    self._completed = [0] * len(cand[0]) + [1] * len(cand[1])
                    LOGGER.debug(f'{self._cand}, {self._order}, {self._completed}')
                    self._numeric = ''
        return self.current()

    # Check if the current yougen is completed
    def is_complete(self):
        current = self.current()
        if not current:
            return True
        if '―' in current:
            return False
        assert '―' in self._yomi
        return False if 0 in self._completed else True

    def get_stem(self, no):
        yomi = self._yomi
        if not yomi:
            return '', ''
        if self._order:
            yomi = yomi[:yomi.find('―') + 1]
            no = self._order[no]
            return yomi, self._dict[yomi][no]
        if self._numeric:
            yomi = '#' + yomi
            cand = self._dict[yomi]
            if len(cand) <= no:
                return yomi, '#' + self._cand[no]
            return yomi, cand[no]
        return yomi, self._cand[no]

    def confirm(self, shrunk) -> int:
        if not self._yomi:
            return 0

        # Get a copy of the original candidate list
        yomi = self._yomi
        no = self._no

        if self._order:
            yomi = yomi[:yomi.find('―') + 1]
            no = self._order[no]
            cand = self._dict[yomi][:]
        elif self._numeric:
            yomi = '#' + yomi
            cand = self._dict[yomi][:]
            if len(cand) <= no:
                cand.append('#' + self._cand[no])
                no = len(cand) - 1
        else:
            cand = self._cand[:]

        # Update the order of the candidates.
        first = cand[no]
        if first == yomi:
            # Ignore pseudo candidates
            return 0
        if 0 < no:
            cand.remove(first)
            cand.insert(0, first)
            self._dict[yomi] = cand
            self._dirty = True

        # Personalize the dictionary if the candidate has been selected by shrinking the reading.
        if shrunk and not self._numeric:
            yomi = shrunk + yomi
            cand = self._dict.get(yomi)
            if cand:
                first = shrunk + first
                cand = cand[:]
                try:
                    cand.remove(first)
                except ValueError:
                    pass
                cand.insert(0, first)
                self._dict[yomi] = cand
                self._dirty = True
                no = 0
            elif yomi[-1] == '―':
                cand = self._dict.get(yomi[:-1])
                if cand:
                    first = shrunk + first
                    self._dict[yomi] = [first]
                    self._dirty = True
                    no = 0

        return no

    def create_pseudo_candidate(self, text):
        LOGGER.debug(f'create_pseudo_candidate("{text}")')
        self._yomi = text
        self._cand = [text]
        self._completed = [0]
        self._no = 0
        self._numeric = ''

    def is_pseudo_candidate(self):
        return self._yomi and self._yomi in self._cand

    def _write_orders(self, filename):
        with open(filename, 'w') as f:
            f.write('; ' + DICTIONARY_VERSION + '\n')
            for yomi, cand in self._dict.items():
                if yomi not in self._dict_base or cand != self._dict_base[yomi]:
                    f.write(yomi + ' /' + '/'.join(cand) + '/\n')

    def save_orders(self):
        if not self._dirty:
            return
        try:
            if not os.path.exists(self._orders_path):
                self._write_orders(self._orders_path)
            else:
                bakfile = self._orders_path + '.bak'
                tmpfile = self._orders_path + '.tmp'
                self._write_orders(tmpfile)
                if os.path.exists(bakfile):
                    os.remove(bakfile)
                os.rename(self._orders_path, bakfile)
                os.rename(tmpfile, self._orders_path)
        except OSError:
            LOGGER.exception(f'could not save the orders in "{self._orders_path}"')
        self._dirty = False

    def use_romazi(self, romazi):
        if romazi:
            self._strdcmp = self.strcmp
        else:
            self._strdcmp = self.strdcmp

    def dump(self):
        print("'", self._yomi, "' ", self._no, ' ', self._cand, sep='')
