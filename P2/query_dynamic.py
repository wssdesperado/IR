import time
import csv
import math
from query import get_line, get_query, pre_process
import argparse


csv.field_size_limit(500 * 1024 * 1024)
stopwords_path = "./stops.txt"


def import_stopwords():
    stopwords = [words for words in open(stopwords_path, 'r', encoding='utf-8', newline='').read().split('\n')]
    return stopwords


def phrase_query(processed_queries):
    stopwords = import_stopwords()
    for query in processed_queries:
        if len(list(query.values())[0].split(' ')) == 1:
            continue
        phrases = []
        terms = (list(query.values())[0]).split(' ')
        for i in range(len(terms) - 1):
            if terms[i] not in stopwords and terms[i + 1] not in stopwords:
                phrases.append(terms[i] + " " + terms[i + 1])
        query[str(list(query.keys())[0])] = phrases
        yield query


def get_lexicon_and_pl_rows(index, index_path):
    with open(index_path + "lexicon_" + index + ".csv", 'r', encoding='utf-8') as f:
        lexicon_reader = csv.reader(f)
        lexicon_column = [column[0] for column in lexicon_reader]
    with open(index_path + "posting_list_" + index + ".csv", 'r', encoding='utf-8') as d:
        pl_reader = csv.reader(d)
        pl_row = [row for row in pl_reader]
    return lexicon_column, pl_row


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


def calculate_bm25(queries, dictionary, index, results_path, index_path):
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


def calculate_positional_bm25(queries, dictionary, index, results_path, index_path):
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
        backup_list = []
        term_idf = {}
        sett = []
        for term in list(query.values())[0]:
            if term not in lexicon_column:
                continue
            term_id = lexicon_column.index(term)
            doc_sublist = eval(posting_list_row[term_id][1]).keys()
            sett.append(list(doc_sublist))
            term_df = eval(posting_list_row[term_id][3])
            idf = math.log((n - term_df + 0.5) / (term_df + 0.5))
            term_idf[term] = idf
        if len(sett) == 1:
            doc_list = list(sett[0])
        elif len(sett) == 0:
            continue
        elif len(sett) == 2:
            for d in sett[0]:
                if d in sett[1]:
                    doc_list.append(d)
            for e in sett[0]:
                if e not in sett[1]:
                    backup_list.append(e)
            for e in sett[1]:
                if e not in sett[0]:
                    backup_list.append(e)
        elif len(sett) >= 3:
            for d in sett[0]:
                if len(sett) == 4:
                    if d in sett[1] and sett[2] and sett[3]:
                        doc_list.append(d)
                    else:
                        backup_list.append(d)
                else:
                    if d in sett[1] and sett[2]:
                        doc_list.append(d)
                    else:
                        backup_list.append(d)

        for doc in doc_list:
            bm25 = 0
            for term in list(query.values())[0]:
                if term not in lexicon_column:
                    continue
                term_id = lexicon_column.index(term)
                if str(term_id) in dictionary[doc][0].keys():
                    f_i = len(dictionary[doc][0][str(term_id)].split(", "))
                    bm25 += term_idf[term] * (f_i * (k1 + 0.5)) / (f_i + k1 * (0.25 + b * (len(dictionary[doc][0]) / mean_length)))
                else:
                    continue
            score_dict[doc] = bm25

        if len(score_dict.keys()) < 100:
            for doc in backup_list:
                bm25 = 0
                for term in list(query.values())[0]:
                    if term not in lexicon_column:
                        continue
                    term_id = lexicon_column.index(term)
                    if str(term_id) in dictionary[doc][0].keys():
                        f_i = len(dictionary[doc][0][str(term_id)].split(", "))
                        bm25 += term_idf[term] * (f_i * (k1 + 0.5)) / (
                                    f_i + k1 * (0.25 + b * (len(dictionary[doc][0]) / mean_length)))
                    else:
                        continue
                score_dict[doc] = bm25

        output_results_txt(score_dict, query, results_path)


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


def main():
    parser = argparse.ArgumentParser(description='dynamic query processing')
    parser.add_argument('index_path', type=str)
    parser.add_argument('query_path', type=str)
    parser.add_argument('results_path', type=str)
    args = parser.parse_args()
    index_path = args.index_path
    query_path = args.query_path
    results_path = args.results_path

    time1 = time.time()
    lines = get_line(query_path)
    queries = get_query(lines)
    processed_queries = pre_process(queries)
    phrased_query = phrase_query(processed_queries)
    phrased_queries = []
    for i in phrased_query:
        phrased_queries.append(i)
    with open(index_path + "lexicon_phrase.csv", 'r', encoding='utf-8') as f:
        lexicon_reader = csv.reader(f)
        lexicon_column = [column[0] for column in lexicon_reader]
    with open(index_path + "posting_list_phrase.csv", 'r', encoding='utf-8') as d:
        pl_reader = csv.reader(d)
        pl_row = [row for row in pl_reader]

    total_phrase_num = 0
    flag = 0
    for query in phrased_queries:
        for term in list(query.values())[0]:
            total_phrase_num += 1
            if term not in lexicon_column:
                flag += 1
                continue
            term_id = lexicon_column.index(term)
            df = int(pl_row[term_id][3])
            if df < 10:
                flag += 1
    if flag > total_phrase_num / 2:
        single_query = []
        for query in phrased_queries:
            q = list(query.keys())[0]
            v = []
            for va in list(query.values())[0]:
                w1 = va.split(' ')[0]
                w2 = va.split(' ')[1]
                if w1 not in v:
                    v.append(w1)
                if w2 not in v:
                    v.append(w2)
            single_query.append({q: v})
        index = "positional"
        dictionary = build_dictionary(index, index_path)
        time2 = time.time()
        print(time2 - time1)
        calculate_positional_bm25(single_query, dictionary, index, results_path, index_path)

    else:
        index = "phrase"
        print("phrase")
        dictionary = build_dictionary(index, index_path)
        time2 = time.time()
        print(time2 - time1)
        calculate_bm25(phrased_queries, dictionary, index, results_path, index_path)
    time3 = time.time()
    print(time3 - time2)


if __name__ == '__main__':
    main()
