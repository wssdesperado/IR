Run the code:
build.py
Parameters (all the parameters are required):
-[trec_files_directory_path]: directory containing the raw documents
-[index_type]: can be one of the following: “single” , “stem” , “phrase”, “positional”
-[output_dir]: the directory where the result index and lexicon files will be written 
-[constraint_size]: memory constraint size (if unlimited memory, the parameter should be 0)
Example: python3 build.py ./BigSample/ single ./result/ 0

query.py
Parameters (all the parameters are required):
- [index-directory-path]: directory contains the lexicons and posting lists
- [query-file-path]: the directory of queryfile.txt
- [retrieval-model]: in this project, only “bm25” is optional
- [index-type]: has to be one of the following: “single”, “stem”
- [results-file]: the directory to generate the output file - results.txt
- [mode]: three options - “expansion”, “reduction” or “hybrid”
- [top-ranked-document]: example: 10, 20…
- [top-ranked-terms]: example: 5, 10…
- [reduction-threshold]: example: 0.5, 0.8… (could be any value in expansion mode)
Example: python3 query.py ./result/ ./queryfile.txt bm25 single ./ expansion 10 20 0.5
Notice: the index type has to be the same as build.py
Output:
(1)	The console will print the running time
(2)	The forward index will store in forward_index.json.
