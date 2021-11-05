import re
import math
import csv
import time
import argparse
from nltk import PorterStemmer


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


def get_line(query_path):
    with open(query_path, 'rt', encoding='utf-8') as f:
        for line in f:
            yield line


def get_query(lines):
    query_num_tag_re = re.compile("<num>")
    query_num_re = re.compile(r"\d+")
    title_tag_re = re.compile("<title>")
    for line in lines:
        if query_num_tag_re.match(line):
            num = query_num_re.search(line).group()
        elif title_tag_re.match(line):
            line = line[15:]
            terms = line.rstrip(' \t\n')
            query = {num: terms}
            yield query
        else:
            continue


def pre_process(queries):
    for query in queries:
        sentence = str(list(query.values())[0])
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
        stopwords = [words for words in open(stopwords_path, 'r').read().split('\n')]
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
        sentence = str.replace(sentence, '/', ' ')
        sentence = str.replace(sentence, '(', ' ')
        sentence = str.replace(sentence, ')', ' ')
        query[str(list(query.keys())[0])] = sentence.lower()
        yield query


def single_term_queries(processed_queries):
    for query in processed_queries:
        sentence = str(list(query.values())[0])
        terms = sentence.split(' ')
        query[str(list(query.keys())[0])] = terms
        yield query


def stem_query(processed_queries):
    stemmer = PorterStemmer()
    for query in processed_queries:
        stemmed_terms = []
        terms = (list(query.values())[0]).split(' ')
        for term in terms:
            stemmed_term = stemmer.stem(term)
            stemmed_terms.append(stemmed_term)
        query[str(list(query.keys())[0])] = stemmed_terms
        yield query


def build_dictionary(index, index_path):
    dictionary = {}
    with open(index_path + "posting_list_" + index + ".csv", 'r', encoding='utf-8') as d:
        d_reader = csv.reader(d)
        rows = [row for row in d_reader]
    flag = 0
    rows = rows[1:]
    for row in rows:
        if len(row) == 0:
            continue
        for key in eval(row[1]).keys():
            if key not in dictionary.keys():
                dictionary.setdefault(key, []).append({row[0]: eval(row[1])[key]})
            else:
                dictionary[key][0][row[0]] = eval(row[1])[key]
    return dictionary


def calculate_query_tf(query):
    tf_dict = {}
    for term in list(query.values())[0]:
        if term in tf_dict:
            tf_dict[term] += 1
        else:
            tf_dict[term] = 1
    return tf_dict


def get_lexicon_and_pl_rows(index, index_path):
    with open(index_path + "lexicon_" + index + ".csv", 'r', encoding='utf-8') as f:
        lexicon_reader = csv.reader(f)
        lexicon_column = [column[0] for column in lexicon_reader]
    with open(index_path + "posting_list_" + index + ".csv", 'r', encoding='utf-8') as d:
        pl_reader = csv.reader(d)
        pl_row = [row for row in pl_reader]
    return lexicon_column, pl_row


def output_results_txt(score_dict, query, results_path):
    score_dict = sorted(score_dict.items(), key=lambda x: x[1], reverse=True)
    num = 1
    with open(results_path + 'results.txt', 'a+') as s:
        for i in dict(score_dict).keys():
            if dict(score_dict)[i] == 0:
                continue
            s.write("{} 0 {} {} {} TfIdf\n".format(list(query.keys())[0], i, num, dict(score_dict)[i]))
            num += 1
            if num > 100:
                break
    return


def calculate_cosine(queries, dictionary, index, index_path, results_path):

    lexicon_column, posting_list_row = get_lexicon_and_pl_rows(index, index_path)

    # 每一条query
    for query in queries:
        tf_dict = calculate_query_tf(query)
        score_dict = {}

        for doc in dictionary.keys():
            numerator = 0
            denominator_right = 0
            denominator_left = 0
            word_list = list(dictionary[doc][0].keys())
            for q_term in tf_dict.keys():
                denominator_left += tf_dict[q_term] ** 2
                if q_term not in lexicon_column:
                    continue
                term_id = lexicon_column.index(q_term)
                if str(term_id) not in word_list:
                    continue
                for d_term in dictionary[doc][0].keys():
                    d_term_idf = math.log10(1765 / int(eval(posting_list_row[int(d_term)][3])))
                    numerator += tf_dict[q_term] * dictionary[doc][0][d_term] * d_term_idf
                    denominator_right += (dictionary[doc][0][d_term] * d_term_idf) ** 2
            if numerator == 0:
                cosine = 0
            else:
                cosine = numerator / (math.sqrt(denominator_left) * math.sqrt(denominator_right))
            score_dict[doc] = cosine
        output_results_txt(score_dict, query, results_path)


def calculate_bm25(queries, dictionary, index, index_path, results_path):
    n = 1765
    k1 = 1.2
    b = 0.75
    length = 0
    for doc in dictionary.keys():
        length += len(dictionary[doc][0])
    mean_length = length / n

    lexicon_column, posting_list_row = get_lexicon_and_pl_rows(index, index_path)

    # 获取所有包含query中任意词的文件列表
    for query in queries:
        score_dict = {}
        doc_list = []
        term_idf = {}
        for term in list(query.values())[0]:
            if term not in lexicon_column:
                continue
            term_id = lexicon_column.index(term)
            doc_sublist = eval(posting_list_row[term_id][1]).keys()
            term_df = eval(posting_list_row[term_id][3])
            idf = math.log((n - term_df + 0.5) / (term_df + 0.5))
            term_idf[term] = idf
            for doc in doc_sublist:
                if doc not in doc_list:
                    doc_list.append(doc)

        for doc in doc_list:
            bm25 = 0
            for term in list(query.values())[0]:
                if term not in lexicon_column:
                    continue
                term_id = lexicon_column.index(term)
                if str(term_id) in dictionary[doc][0].keys():
                    f_i = dictionary[doc][0][str(term_id)]
                    bm25 += term_idf[term] * (f_i * (k1 + 0.5)) / (f_i + k1 * (0.25 + b * (len(dictionary[doc][0]) / mean_length)))
                else:
                    continue
            score_dict[doc] = bm25

        output_results_txt(score_dict, query, results_path)


def query_likelihood(queries, dictionary, index, index_path, results_path):
    length = 0
    for doc in dictionary.keys():
        length += len(dictionary[doc][0])
    mean_length = length / 1765

    lexicon_column, posting_list_row = get_lexicon_and_pl_rows(index, index_path)
    for query in queries:
        score_dict = {}
        doc_list = []
        term_tf = {}
        for term in list(query.values())[0]:
            if term not in lexicon_column:
                continue
            term_id = lexicon_column.index(term)
            doc_sublist = eval(posting_list_row[term_id][1]).keys()
            term_tf[term] = int(posting_list_row[term_id][2])
            for doc in doc_sublist:
                if doc not in doc_list:
                    doc_list.append(doc)

        for doc in doc_list:
            prob = 0
            for term in list(query.values())[0]:
                if term not in lexicon_column:
                    continue
                term_id = lexicon_column.index(term)
                if str(term_id) in dictionary[doc][0].keys():
                    prob -= math.log((dictionary[doc][0][str(term_id)] + mean_length * term_tf[term] / length) / (len(dictionary[doc][0]) + mean_length))
                else:
                    continue
            score_dict[doc] = prob
        output_results_txt(score_dict, query, results_path)


def main():
    parser = argparse.ArgumentParser(description="static query processing")
    parser.add_argument('index_path', type=str)
    parser.add_argument('query_path', type=str)
    parser.add_argument('model', type=str)
    parser.add_argument('index', type=str)
    parser.add_argument('results_path', type=str)
    args = parser.parse_args()
    index_path = args.index_path
    query_path = args.query_path
    model = args.model
    index = args.index
    results_path = args.results_path

    time1 = time.time()
    lines = get_line(query_path)
    queries = get_query(lines)
    processed_queries = pre_process(queries)
    queries_format = {}
    if index == "single":
        queries_format = single_term_queries(processed_queries)
    elif index == "stem":
        queries_format = stem_query(processed_queries)
    dictionary = build_dictionary(index, index_path)
    time2 = time.time()
    print(time2 - time1)
    if model == "cosine":
        calculate_cosine(queries_format, dictionary, index, index_path, results_path)
    elif model == "bm25":
        calculate_bm25(queries_format, dictionary, index, index_path, results_path)
    elif model == "lm":
        query_likelihood(queries_format, dictionary, index, index_path, results_path)
    time3 = time.time()
    print(time3 - time2)


if __name__ == '__main__':
    main()
