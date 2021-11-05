import argparse
import csv
import os
import re
import string
from nltk.stem import *
import shutil
import time

csv.field_size_limit(500 * 1024 * 1024)

escape_sequences = {
    '&lt': "<",
    '&gt': ">",
    '&amp': "&",
    '&quot': "\"",
    '&apos': "'",
    '&cent': "¢",
    '&pound': "£",
    '&yen': "¥",
    '&euro': "€",
    '&copy': "©",
    '&reg': "®",
    '&blank': " ",
    '&hyph': "-",
    '&sect': "§",
    '&times': "×",
    '&bull': "•",
    '&cir': "ˆ",
    '&mu': "μ",
    '&para': "¶",
    '&rsquo': "’",
    '&ge': "≥",

}

monetary_symbols = ['￥', '$', '€', '￡', '円', 'HKD', 'HK$', '¢', '€']

prefixes = ['pro', 'pre', 're', 'de']

stopwords_path = "./stops.txt"



def import_stopwords():
    stopwords = [words for words in open(stopwords_path, 'r', encoding='utf-8', newline='').read().split('\n')]
    return stopwords


def generate_file_sentences(filename, trec_files_directory_path):
    """

    Reads a file line-by-line (doesn't read entire file into memory)

    :param filename:
    :return: one line of text in str
    """
    with open(trec_files_directory_path + str(filename), 'rt') as f:
        for line in f:
            yield line


def capture_doc(sentences):
    """

    Extract one doc with DOC_ID and corresponding TEXT, then return in DICT

    :param sentences: a string of sentences
    :return: a Dict of sentences of text of a particular doc
             e.g.: {'FR940303-1-00002': ['DEPARTMENT OF TRANSPORTATION', 'Federal Aviation Administration']}
    """
    docno = str
    flag = 0
    doc_text = []
    docno_start = re.compile("<DOCNO>")
    text_start = re.compile("<TEXT>")
    comment = re.compile("<!")
    text_end = re.compile("</TEXT>")
    tag_start = re.compile("<[A-Z]+>")
    tag_end = re.compile("</[A-Z]+>")
    space = re.compile(r" \n")
    for sentence in sentences:
        # DOC_ID
        if len(sentence) == 0:
            continue
        elif docno_start.match(sentence):
            index = 0
            sentence_list = list(sentence)
            for character in sentence_list:
                if character != '>':
                    index += 1
                    continue
                else:
                    index += 2
                    break
            del sentence_list[0:index]
            index = -1
            for character in sentence_list[::-1]:
                if character != '<':
                    index -= 1
                else:
                    index -= 1
                    break
            del sentence_list[index:-1]  # delete tag and end tag
            del sentence_list[-1]  # delete '\n'
            sentence = ''.join(sentence_list)
            docno = sentence
        # <TEXT>
        elif text_start.match(sentence):
            flag = 1
        # comments: <!-- -->
        elif comment.search(sentence):
            continue
        elif tag_end.match(sentence) and not text_end.match(sentence):
            continue
        # </TEXT>
        elif text_end.match(sentence):
            flag = 0
            dict_docno_text = {docno: doc_text}
            yield dict_docno_text
            doc_text.clear()
        # <XXX>text text text</XXX>
        elif tag_start.search(sentence) and not text_start.search(sentence) and flag == 1:
            sentence_list = list(sentence)
            index = 0
            for character in sentence_list:
                if character != '>':
                    index += 1
                    continue
                else:
                    index += 1
                    break
            del sentence_list[0:index]
            index = -1
            for character in sentence_list[::-1]:
                if character != '<':
                    index -= 1
                else:
                    break
            del sentence_list[index:-1]  # delete tag and end tag
            del sentence_list[-1]  # delete '\n'
            sentence = ''.join(sentence_list)
            handled_sentence = handle_special_tokens(sentence)
            if len(sentence) == 0:
                continue
            doc_text.append(handled_sentence)
        elif space.match(sentence):
            continue
        elif sentence[0] != '\n' and flag == 1:
            if len(sentence) == 1 and sentence[0] == " ":
                continue
            sentence = str.replace(sentence, '\n', '')
            handled_sentence = handle_special_tokens(sentence)
            doc_text.append(handled_sentence)
        else:
            continue


def handle_special_tokens(sentence):
    # escape sequences
    for escape_sequence in escape_sequences.keys():
        sentence = str.replace(sentence, escape_sequence, escape_sequences[escape_sequence])
    # monetary symbols
    for symbol in monetary_symbols:
        sentence = str.replace(sentence, symbol, '')
    # alphabet-digit
    alphabet_digit = re.compile(r'[A-Za-z]+-\d+')
    for combination in alphabet_digit.findall(sentence):
        alphabets = re.findall('[A-Za-z]+', ''.join(combination))
        digits = re.findall(r'\d+', ''.join(combination))
        if len(''.join(alphabets)) >= 3:
            sentence = str.replace(sentence, combination,
                                   ''.join(alphabets).lower() + ' ' + ''.join(alphabets).lower() + ''.join(digits))
        else:
            sentence = str.replace(sentence, combination, ''.join(alphabets).lower() + ''.join(digits))
    # digit-alphabet
    digit_alphabet = re.compile(r'\d+-[A-Za-z]+')
    for combination in digit_alphabet.findall(sentence):
        alphabets = re.findall('[A-Za-z]+', ''.join(combination))
        digits = re.findall(r'\d+', ''.join(combination))
        if len(''.join(alphabets)) >= 3:
            sentence = str.replace(sentence, combination,
                                   ''.join(alphabets).lower() + ' ' + ''.join(digits) + ''.join(alphabets).lower())
        else:
            sentence = str.replace(sentence, combination, ''.join(digits).lower() + ''.join(alphabets).lower())
    # date
    valid_date_format = re.compile(
        r'(?:(?:(?:(?:0[13578]|1[02])(?:-|/)(?:0[1-9]|[12][0-9]|3[01]))|(?:(?:0[469]|11)(?:-|/)(?:0[1-9]|[12][0-9]|30))|(?:02-(?:0[1-9]|[1][0-9]|2[0-8])))(?:-|/)(?:[0-9]{3}[1-9]|[0-9]{2}[1-9][0-9]{1}|[0-9]{1}[1-9][0-9]{2}|[1-9][0-9]{3}))|02(?:-|/)29(?:-|/)(?:(?:[0-9]{2})(?:0[48]|[2468][048]|[13579][26])|(?:(?:0[48]|[2468][048]|[3579][26])00))')
    invalid_date_format_1 = re.compile(
        r'(?:(?:Jan\.*)|(?:Feb\.*)|(?:Mar\.*)|(?:Apr\.*)|(?:Jun\.*)|(?:Jul\.*)|(?:Aug\.*)|(?:Sept\.*)|(?:Oct\.*)|(?:Nov\.*)|(?:Dec\.*)|(?:January)|(?:February)|(?:March)|(?:April)|(?:May)|(?:June)|(?:July)|(?:August)|(?:September)|(?:October)|(?:November)|(?:December)) [0-9][0-9], [0-9]{1,4}')
    # format: month_name DD, YYYY   including invalid test
    for invalid_date in invalid_date_format_1.findall(sentence):
        months = re.findall(r'[A-Za-z]+\.* ', ''.join(invalid_date))
        formatted_months = ""
        for month in months:
            if month == "January" or "Jan" or "Jan.":
                formatted_months = str.replace(''.join(months), month, "01-")
            elif month == "February" or "Feb" or "Feb.":
                formatted_months = str.replace(''.join(months), month, "02-")
            elif month == "March" or "Mar" or "Mar.":
                formatted_months = str.replace(''.join(months), month, "03-")
            elif month == "April" or "Apr" or "Apr.":
                formatted_months = str.replace(''.join(months), month, "04-")
            elif month == "May":
                formatted_months = str.replace(''.join(months), month, "05-")
            elif month == "June" or "Jun" or "Jun.":
                formatted_months = str.replace(''.join(months), month, "06-")
            elif month == "July" or "Jul" or "Jul.":
                formatted_months = str.replace(''.join(months), month, "07-")
            elif month == "August" or "Aug" or "Aug.":
                formatted_months = str.replace(''.join(months), month, "08-")
            elif month == "September" or "Sept" or "Sept.":
                formatted_months = str.replace(''.join(months), month, "09-")
            elif month == "October" or "Oct" or "Oct.":
                formatted_months = str.replace(''.join(months), month, "10-")
            elif month == "November" or "Nov" or "Nov.":
                formatted_months = str.replace(''.join(months), month, "11-")
            elif month == "December" or "Dec" or "Dec.":
                formatted_months = str.replace(''.join(months), month, "12-")
            formatted_date = str.replace(invalid_date, month, formatted_months)
            formatted_date = str.replace(formatted_date, ", ", "-")
            if valid_date_format.findall(formatted_date):
                sentence = str.replace(sentence, invalid_date, formatted_date)
            else:
                sentence = str.replace(sentence, invalid_date, '')
    # format: MMMM/DDDD/YYYY & MMMM-DDDD-YYYY
    invalid_date_format_2 = re.compile(r'[0-9]{1,4}(?:/|-)[0-9]{1,4}(?:/|-)[0-9]{1,4}')
    for invalid_date in invalid_date_format_2.findall(sentence):
        invalid_date = str.replace(invalid_date, "/", "-")
        if valid_date_format.match(invalid_date):
            sentence = str.replace(sentence, invalid_date, invalid_date)
        else:
            sentence = str.replace(sentence, invalid_date, '')
    # date_format_1 = re.compile(r'((((0[13578]|1[02])-(0[1-9]|[12][0-9]|3[01]))|((0[469]|11)-(0[1-9]|[12][0-9]|30))|(02-(0[1-9]|[1][0-9]|2[0-8])))-([0-9]{3}[1-9]|[0-9]{2}[1-9][0-9]{1}|[0-9]{1}[1-9][0-9]{2}|[1-9][0-9]{3}))|02-29-(([0-9]{2})(0[48]|[2468][048]|[13579][26])|((0[48]|[2468][048]|[3579][26])00))')
    # date_format_2 = re.compile(r'((((0[13578]|1[02])/(0[1-9]|[12][0-9]|3[01]))|((0[469]|11)/(0[1-9]|[12][0-9]|30))|(02-(0[1-9]|[1][0-9]|2[0-8])))/([0-9]{3}[1-9]|[0-9]{2}[1-9][0-9]{1}|[0-9]{1}[1-9][0-9]{2}|[1-9][0-9]{3}))|02/29/(([0-9]{2})(0[48]|[2468][048]|[13579][26])|((0[48]|[2468][048]|[3579][26])00))')
    # format: MM-DD-YYYY & MM/DD/YYYY
    for date in valid_date_format.findall(sentence):
        formatted_date = str.replace(date, '/', '-')
        sentence = str.replace(sentence, date, formatted_date)
    # digit formats
    digit_format = re.compile(r'[0-9]+,+[0-9]+.*[0-9]*')
    for digits in digit_format.findall(sentence):
        unified_digits = str.replace(digits, ",", '')
        sentence = str.replace(sentence, digits, unified_digits)
    # hyphenated terms
    hyphenated_terms = re.compile(r'[a-zA-Z]+-[a-zA-Z]+(?:-[a-zA-Z]+)?')
    stopwords = [words for words in open(stopwords_path, 'r', encoding='utf-8', newline='').read().split('\n')]
    for combination in hyphenated_terms.findall(sentence):
        alphabets = re.findall(r'[a-zA-Z]+', combination)
        substitution = ""
        for word in alphabets:
            if len(word) > 1 and word not in stopwords:
                substitution += ''.join(word)
                substitution += " "
        sentence = str.replace(sentence, combination, substitution + ''.join(alphabets))
    # file extensions
    file_extensions = re.compile(
        r'(?:\d*|\w*).(?:(?:pdf)|(?:java)|(?:xml)|(?:conf)|(?:txt)|(?:xls)|(?:doc)|(?:ppt)|(?:exe)|(?:html)|(?:jpg)|(?:rmvb)|(?:avi))')
    for extensions in file_extensions.findall(sentence):
        extension = str.replace(extensions, ".", " ")
        sentence = str.replace(sentence, extensions, extension)
    # email address
    email_address_reg = re.compile(r'^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(?:\.[a-zA-Z0-9_-]+)+$')
    for email in email_address_reg.findall(sentence):
        print(email)
    # ip address
    ip_address_reg = re.compile(
        r'^(?:1\d{2}|2[0-4]\d|25[0-5]|[1-9]\d|[1-9])\.(?:1\d{2}|2[0-4]\d|25[0-5]|[1-9]\d|\d)\.(?:1\d{2}|2[0-4]\d|25[0-5]|[1-9]\d|\d)\.(?:1\d{2}|2[0-4]\d|25[0-5]|[1-9]\d|\d)$')
    for ip in ip_address_reg.findall(sentence):
        print(ip)
    # urls
    url_reg = re.compile(r'\b(?:(?:[\w-]+://?|www[.])[^\s()<>]+(?:[\w\d]+|(?:[^[:punct:]\s]|/)))')
    for url in url_reg.findall(sentence):
        print(url)
    # abbreviation
    abbreviation = re.compile(r'[A-Za-z]{1,2}\.+(?:[A-Za-z]+\.*)+')
    matched_strings = abbreviation.findall(sentence)
    # remove punctuations
    punctuation_reg = re.compile(r'(?:\. )|(?:, )|(?:! )|(?:\? )|(?:: )')
    for punctuations in re.findall(r'[,;]', sentence):
        sentence = str.replace(sentence, punctuations, ' ')
    for punctuation in punctuation_reg.findall(sentence):
        sentence = str.replace(sentence, punctuation, " ")
    for word in matched_strings:
        translator = str.maketrans('', '', '.')
        words_without_dots = word.translate(translator)
        lower_words_without_dots = words_without_dots.lower()
        sentence = str.replace(sentence, word, lower_words_without_dots)
    return sentence.lower()


def generate_single_term_index(sentence, lexicon, posting_list, term_id, mode, file_num, constraint_size):
    stopwords = import_stopwords()
    doc_no = ''.join(sentence.keys())
    translator = str.maketrans('', '', string.punctuation)
    position = 0
    for words in sentence.values():
        for wordlist in words:
            for word in wordlist.split():
                position += 1
                word = str.lstrip(word, r'[!"#$%&\'()*+,-./:;<=>?@\[\\\]^_`{|}~]')
                word = str.rstrip(word, r'[!"#$%&\'()*+,-./:;<=>?@\[\\\]^_`{|}~]')
                if word in stopwords and mode == 1:
                    continue
                if word in string.punctuation:
                    continue
                if word.translate(translator) == '':
                    continue
                # single-term index
                if mode == 1:
                    term_id, file_num = update_lexicon_and_posting_list(lexicon, posting_list, word, doc_no, term_id, file_num, constraint_size)
                # single-term index with position information
                else:
                    if word in lexicon:
                        index = lexicon[word]
                        if index in posting_list.keys():
                            posting_list[index][1] += 1
                            if doc_no in list(posting_list[index][0].keys()):
                                posting_list[index][0][doc_no] += ", " + str(position)
                            else:
                                posting_list[index][0][doc_no] = str(position)
                        else:
                            if constraint_size != 0 and len(posting_list.keys()) >= constraint_size:
                                file_num = generate_temp_files_for_merging(posting_list, file_num)
                            posting_list.setdefault(index, []).append({doc_no: str(position)})
                            posting_list.setdefault(index, []).append(1)
                    else:
                        if constraint_size != 0 and len(posting_list.keys()) >= constraint_size:
                            file_num = generate_temp_files_for_merging(posting_list, file_num)
                        lexicon.setdefault(word, term_id)
                        posting_list.setdefault(term_id, []).append({doc_no: str(position)})
                        posting_list.setdefault(term_id, []).append(1)
                        term_id += 1
    return term_id, file_num


def generate_phrase_index(sentence, lexicon, posting_list, term_id, file_num, constraint_num):
    stopwords = import_stopwords()
    doc_no = ''.join(sentence.keys())
    for words in sentence.values():
        for word_list in words:
            temp = word_list.split()
            if len(temp) <= 1:
                continue
            elif len(temp) == 2:
                if temp[0].isalnum() and temp[0] not in stopwords and temp[1].isalnum() and temp[1] not in stopwords:
                    phrase = temp[0] + " " + temp[1]
                    term_id, file_num = update_lexicon_and_posting_list(lexicon, posting_list, phrase, doc_no, term_id,
                                                                        file_num, constraint_num)
            elif len(temp) > 2:
                for i in range(0, len(temp)):
                    if not temp[i].isalnum():
                        continue
                    if i == len(temp) - 1:
                        break
                    if temp[i] in stopwords:
                        continue
                    if temp[i + 1] not in stopwords and temp[i + 1].isalnum():
                        phrase = temp[i] + " " + temp[i + 1]
                        term_id, file_num = update_lexicon_and_posting_list(lexicon, posting_list, phrase, doc_no,
                                                                            term_id, file_num, constraint_num)
                        if i < len(temp) - 2:
                            if temp[i + 2].isalnum() and temp[i + 2] not in stopwords:
                                phrase = temp[i] + " " + temp[i + 1] + " " + temp[i + 2]
                                term_id, file_num = update_lexicon_and_posting_list(lexicon, posting_list, phrase,
                                                                                    doc_no, term_id, file_num,
                                                                                    constraint_num)
    return term_id, file_num


def update_lexicon_and_posting_list(lexicon, posting_list, term, doc_no, term_id, file_num, constraint_size):
    if term in lexicon.keys():
        index = lexicon[term]
        if index in posting_list.keys():
            posting_list[index][1] += 1
            if doc_no in posting_list[index][0].keys():
                posting_list[index][0][doc_no] += 1
                return term_id, file_num
            else:
                posting_list[index][0][doc_no] = 1
        else:
            if constraint_size != 0 and len(posting_list.keys()) >= constraint_size:
                file_num = generate_temp_files_for_merging(posting_list, file_num)
            posting_list.setdefault(index, []).append(doc_no)
            posting_list.setdefault(index, []).append(1)
    else:
        if constraint_size != 0 and len(posting_list.keys()) >= constraint_size:
            file_num = generate_temp_files_for_merging(posting_list, file_num)
        lexicon.setdefault(term, term_id)
        posting_list.setdefault(term_id, []).append({doc_no: 1})
        posting_list.setdefault(term_id, []).append(1)
        term_id = term_id + 1
    return term_id, file_num


def generate_stem_index(sentence, lexicon, posting_list, term_id, file_num, constraint_size):
    stemmer = PorterStemmer()
    doc_no = ''.join(sentence.keys())
    for words in sentence.values():
        for wordlist in words:
            for word in wordlist.split():
                if word.isalnum():
                    stemmed_word = stemmer.stem(word)
                    term_id, file_num = update_lexicon_and_posting_list(lexicon, posting_list, stemmed_word, doc_no, term_id, file_num, constraint_size)
    return term_id, file_num


def generate_output_csv(lexicon, posting_list, mode, file_num, constraint_size, output_dir):
    index = ""
    if mode == 1:
        index = "single"
    elif mode == 2:
        index = "positional"
    elif mode == 3:
        index = "phrase"
    elif mode == 4:
        index = "stem"
    if os.path.exists(output_dir+"lexicon_" + index + ".csv"):
        os.remove(output_dir+"lexicon_" + index + ".csv")
    if os.path.exists(output_dir+"posting_list_" + index + ".csv"):
        os.remove(output_dir+"posting_list.csv")
    lexicon_f = open(output_dir+"lexicon_" + index + ".csv", 'a', encoding='utf-8', newline='')
    csv_lexicon = csv.writer(lexicon_f)
    csv_lexicon.writerow(('term', 'term_id'))
    if constraint_size != 0:
        posting_list_f = open("./temp/" + str(file_num) + ".csv", 'a', encoding='utf-8', newline='')
        csv_posting_list = csv.writer(posting_list_f)
    else:
        posting_list_f = open(output_dir+"posting_list_" + index + ".csv", 'a', encoding='utf-8', newline='')
        csv_posting_list = csv.writer(posting_list_f)
        csv_posting_list.writerow(('term_id', 'doc_id', 'term_frequency', 'df'))

    # lexicon = sorted(lexicon, key=lambda x: x)
    if constraint_size == 0:
        num = 1
        for term in lexicon:
            index = lexicon[term]
            if mode == 3:
                if posting_list[index][1] >= 6:
                    csv_lexicon.writerow((term, num))
                    csv_posting_list.writerow((num, posting_list[index][0], posting_list[index][1], len(posting_list[index][0].values())))
                    num += 1
            elif mode == 2:
                csv_lexicon.writerow((term, index))
                csv_posting_list.writerow((index, posting_list[index][0], posting_list[index][1], len(posting_list[index][0].keys())))
            else:
                csv_lexicon.writerow((term, index))
                csv_posting_list.writerow((index, posting_list[index][0], posting_list[index][1], len(posting_list[index][0].values())))
    else:
        for term_id in posting_list.keys():
            csv_posting_list.writerow((term_id, posting_list[term_id][0], posting_list[term_id][1]))
    posting_list_f.close()
    time_2 = time.time()
    if constraint_size != 0:
        for term in lexicon:
            csv_lexicon.writerow((term, lexicon[term]))
        merge(file_num, output_dir)
    return time_2


def generate_temp_files_for_merging(posting_list, file_num):
    with open("./temp/" + str(file_num) + ".csv", 'a', encoding='utf-8', newline='') as temp_file:
        sorted_posting_list = sorted(posting_list, key=lambda x: x)
        temp_file_writer = csv.writer(temp_file)
        for term_id in sorted_posting_list:
            temp_file_writer.writerow((term_id, posting_list[term_id][0], posting_list[term_id][1]))
    posting_list.clear()
    file_num += 1
    return file_num


def merge(file_num, output_dir):
    result_num = 1
    if file_num == 1:
        posting_list_csv = open(output_dir+"posting_list.csv", 'a', encoding='utf-8', newline='')
        posting_list_writer = csv.writer(posting_list_csv)
        posting_list_writer.writerow(("term_id", "doc_id", "frequency"))
        temp_file_csv = open("./temp/" + str(file_num) + ".csv", 'r+', encoding='utf-8', newline='')
        temp_file_reader = csv.reader(temp_file_csv)
        for line in temp_file_reader:
            posting_list_writer.writerow((line[0], line[1], line[2]))
    else:
        temp_result = open("./temp/result" + str(result_num) + ".csv", 'a', encoding='utf-8', newline='')
        temp_result_writer = csv.writer(temp_result)
        with open("./temp/" + str(1) + ".csv", 'r+', encoding='utf-8', newline='') as f:
            reader = csv.reader(f)
            row_1 = [row for row in reader]
        with open("./temp/" + str(2) + ".csv", 'r+', encoding='utf-8', newline='') as f:
            reader = csv.reader(f)
            row_2 = [row for row in reader]
        i = j = 0
        while i < len(row_1) and j < len(row_2):
            if row_1[i][0] == row_2[j][0]:
                if row_1[i][1].find(row_2[j][1]) != -1:
                    print(int(row_1[i][2]) + int(row_2[j][2]))
                    temp_result_writer.writerow((row_1[i][0], row_1[i][1],
                                                 (int(row_1[i][2]) + int(row_2[j][2]))))
                elif row_1[i][1].find(row_2[j][1]) == -1:
                    print(int(row_1[i][2]) + int(row_2[j][2]))
                    temp_result_writer.writerow((row_1[i][0],
                                                 row_1[i][1] + ", " + row_2[j][1],
                                                 (int(row_1[i][2]) + int(row_2[j][2]))))
                i += 1
                j += 1
            elif row_1[i][0] < row_2[j][0]:
                temp_result_writer.writerow((row_1[i][0], row_1[i][1],
                                             row_1[i][2]))
                i += 1
            else:
                temp_result_writer.writerow((row_2[j][0], row_2[j][1],
                                             row_2[j][2]))
                j += 1
        if i == len(row_1):
            for j in range(j, len(row_2)):
                temp_result_writer.writerow(
                    (row_2[j][0], row_2[j][1], row_2[j][2]))
        else:
            for i in range(i, len(row_1)):
                temp_result_writer.writerow(
                    (row_1[i][0], row_1[i][1], row_1[i][2]))
        temp_result.close()
        result_num += 1
        if file_num >= 3:
            for num in range(3, file_num + 1):
                with open("./temp/result" + str(result_num - 1) + ".csv", 'r+', encoding='utf-8', newline='') as temp_result:
                    temp_result_reader = csv.reader(temp_result)
                    row_r = [row for row in temp_result_reader]
                temp_result_new = open("./temp/result" + str(result_num) + ".csv", 'a', encoding='utf-8', newline='')
                temp_result_new_writer = csv.writer(temp_result_new)
                with open("./temp/" + str(num) + ".csv", 'r', encoding='utf-8', newline='') as temp_file_next:
                    temp_file_next_reader = csv.reader(temp_file_next)
                    row_3 = [row for row in temp_file_next_reader]
                m = n = 0
                while m < len(row_r) and n < len(row_3):
                    if row_r[m][0] == row_3[n][0]:
                        if row_r[m][1].find(row_3[n][1]) != -1:
                            temp_result_new_writer.writerow((row_r[m][0], row_r[m][1],
                                                             int(row_r[m][2]) + int(row_3[n][2])))
                        elif row_r[m][1].find(row_3[n][1]) == -1:
                            temp_result_new_writer.writerow((row_r[m][0],
                                                             row_r[m][1] + ", " + row_3[n][1],
                                                             int(row_r[m][2]) + int(row_3[n][2])))
                        m += 1
                        n += 1
                    elif row_r[m][0] < row_3[n][0]:
                        temp_result_new_writer.writerow((row_r[m][0], row_r[m][1],
                                                         row_r[m][2]))
                        m += 1
                    else:
                        temp_result_new_writer.writerow((row_3[n][0], row_3[n][1],
                                                         row_3[n][2]))
                        n += 1
                if m == len(row_r):
                    for n in range(n, len(row_3)):
                        temp_result_new_writer.writerow(
                            (row_3[n][0], row_3[n][1], row_3[n][2]))
                else:
                    for m in range(m, len(row_r)):
                        temp_result_new_writer.writerow(
                            (row_r[m][0], row_r[m][1], row_r[m][2]))
                temp_result_new.close()
                result_num += 1
        posting_list_csv = open(output_dir+"posting_list.csv", 'a', encoding='utf-8', newline='')
        posting_list_writer = csv.writer(posting_list_csv)
        posting_list_writer.writerow(("term_id", "doc_id", "frequency", "df"))
        with open("./temp/result" + str(result_num - 1) + ".csv", 'r+', encoding='utf-8', newline='') as temp_result:
            temp_result_reader = csv.reader(temp_result)
            for line in temp_result_reader:
                posting_list_writer.writerow((line[0], line[1], line[2], len(line[1].split(", "))))


def main():
    time_1 = time.time()
    parser = argparse.ArgumentParser(description='generate inverted index')
    parser.add_argument('trec_files_directory_path', type=str)
    parser.add_argument('index_type', type=str)
    parser.add_argument('output_dir', type=str)
    parser.add_argument('constraint_size', type=int)
    args = parser.parse_args()
    trec_files_directory_path = args.trec_files_directory_path
    output_dir = args.output_dir
    constraint_size = args.constraint_size
    index_type = args.index_type
    if index_type == "single":
        mode = 1
    elif index_type == "positional":
        mode = 2
    elif index_type == "phrase":
        mode = 3
    elif index_type == "stem":
        mode = 4
    else:
        print("Wrong Parameter!")
        return
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    posting_list = {}
    lexicon = {}
    term_id = 1
    file_num = 0
    if constraint_size is not None:
        file_num = 1
        if not os.path.exists("./temp/"):
            os.mkdir("./temp")
        else:
            shutil.rmtree("./temp/")
            os.mkdir("./temp/")
    for filename in os.listdir(trec_files_directory_path):
        if filename == ".DS_Store":
            continue
        sentences = generate_file_sentences(filename, trec_files_directory_path)
        raw_text = capture_doc(sentences)
        for sentence in raw_text:
            if mode == 1 or mode == 2:
                term_id, file_num = generate_single_term_index(sentence, lexicon, posting_list, term_id, mode, file_num, constraint_size)
            elif mode == 3:
                term_id, file_num = generate_phrase_index(sentence, lexicon, posting_list, term_id, file_num,
                                                          constraint_size)
            elif mode == 4:
                term_id, file_num = generate_stem_index(sentence, lexicon, posting_list, term_id, file_num, constraint_size)
    time_2 = generate_output_csv(lexicon, posting_list, mode, file_num, constraint_size, output_dir)
    time_3 = time.time()
    if constraint_size != 0:
        print("Time taken to create temporary files (up to merging) is ", time_2 - time_1, 's')
        print("Time taken to merge temp files is ", time_3 - time_2, 's')
        print("Time taken to build Inverted Index in milliseconds (the whole process from reading documents to building inverted index) is ", time_3 - time_1, 's')


if __name__ == '__main__':
    main()
