from tqdm import tqdm
import util as UTIL
from collections import Counter
#from random import shuffle,random
import random
def convert_idx(text, tokens):
    current = 0
    spans = []
    for token in tokens:
        current = text.find(token, current)
        if current < 0:
            print("Token {} cannot be found".format(token))
            raise Exception()
        spans.append((current, current + len(token)))
        current += len(token)
    return spans

def process_squad_file(data, word_counter, char_counter):
    print("Generating examples...")
    examples = []
    eval_examples = {}
    total,_i_para  = 0, 0
    questions = []
    paragraphs = []
    question_to_paragraph = []
    for article in tqdm(data["data"]):
        title = article["title"]
        for para in article["paragraphs"]:
            context = para["context"].replace(
                "''", '" ').replace("``", '" ')
            paragraphs.append(context)
            context_tokens = UTIL.word_tokenize(context)
            context_chars = [list(token) for token in context_tokens]
            spans = convert_idx(context, context_tokens)
            for token in context_tokens:
                word_counter[token] += len(para["qas"])
                for char in token:
                    char_counter[char] += len(para["qas"])
            for qa in para["qas"]:
                total += 1
                ques = qa["question"].replace(
                    "''", '" ').replace("``", '" ')
                questions.append(ques)
                question_to_paragraph.append(_i_para)
                ques_tokens = UTIL.word_tokenize(ques)
                ques_chars = [list(token) for token in ques_tokens]
                for token in ques_tokens:
                    word_counter[token] += 1
                    for char in token:
                        char_counter[char] += 1
                y1s, y2s = [], []
                answer_texts = []
                for answer in qa["answers"]:
                    answer_text = answer["text"]
                    answer_start = answer['answer_start']
                    answer_end = answer_start + len(answer_text)
                    answer_texts.append(answer_text)
                    answer_span = []
                    for idx, span in enumerate(spans):
                        if not (answer_end <= span[0] or answer_start >= span[1]):
                            answer_span.append(idx)
                    y1, y2 = answer_span[0], answer_span[-1]
                    y1s.append(y1)
                    y2s.append(y2)
                example = {"context_tokens": context_tokens, "context_chars": context_chars, "ques_tokens": ques_tokens,
                           "ques_chars": ques_chars, "y1s": y1s, "y2s": y2s, "id": total}
                examples.append(example)
                eval_examples[str(total)] = {
                    "context": context, "spans": spans, 'ques': ques,"answers": answer_texts, "uuid": qa["id"], 'title': title}
            _i_para += 1
    print("{} questions in total".format(len(examples)))
    return examples, eval_examples, questions, paragraphs, question_to_paragraph
def tokenize_contexts(contexts:list, max_tokens=-1):
    tokenized_context = [UTIL.word_tokenize(context.strip()) if max_tokens == -1 else UTIL.word_tokenize(context.strip())[0:max_tokens]for context in contexts]
    return tokenized_context

def fixing_the_token_problem(tokenized_questions, tokenized_paragraphs):
    # fixing the '' problem:
    fixed_tokenized_question = []
    for indx, question in enumerate(tokenized_questions):
        tokens = []
        for token in question:
            t = token.strip()
            if t != "":
                tokens.append(t)
        fixed_tokenized_question.append(tokens)

    fixed_tokenized_paragraph = []
    for indx, paragraph in enumerate(tokenized_paragraphs):
        tokens = []
        for token in paragraph:
            t = token.strip()
            if t != "":
                tokens.append(t)
        fixed_tokenized_paragraph.append(tokens)
    return fixed_tokenized_question, fixed_tokenized_paragraph

def yield_to_matchzoo(question_answer_content, negative_sampling_count=100, max_tokens=-1):
    """
    :param question_answer_document content:
    :return: yield matchzoo data
    At initial version, we are just focusing on the context and question, nothing more,
    therefore we are ignoring the answer part as of now
    """
    word_counter, char_counter = Counter(), Counter()
    examples, eval, questions, paragraphs, q_to_ps = process_squad_file(question_answer_content, word_counter, char_counter)
    tokenized_paragraphs = tokenize_contexts(paragraphs, max_tokens)
    tokenized_questions = tokenize_contexts(questions, max_tokens)
    tokenized_questions, tokenized_paragraphs = fixing_the_token_problem(tokenized_questions, tokenized_paragraphs)

    paragraphs_nontokenized = [" ".join(context) for context in tokenized_paragraphs]
    questions_nontokenized = [" ".join(context) for context in tokenized_questions]

    for q_indx, question in enumerate(tqdm(questions_nontokenized)):
        true_p_indx = q_to_ps[q_indx]
        true_paragraph = paragraphs_nontokenized[true_p_indx]
        temp_list = paragraphs_nontokenized.copy()
        del temp_list[true_p_indx]
        random.Random(q_indx).shuffle(temp_list)
        for p_indx, paragraph in enumerate([true_paragraph] + temp_list[:negative_sampling_count]):
            yield '\t'.join(['1' if p_indx == 0 else '0', question, paragraph])

