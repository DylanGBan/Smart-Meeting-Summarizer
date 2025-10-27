import logging
import re
import os
from collections import defaultdict
from typing import Iterable
import spacy
from spacy.tokens import Span
from dotenv import load_dotenv
from openai import OpenAI

logger = logging.getLogger(__name__)

ACTION_VERBS = {
    "assign",
    "collaborate",
    "decide",
    "discuss",
    "draft",
    "finalize",
    "fix",
    "follow",
    "migrate",
    "present",
    "review",
    "schedule",
    "send",
    "ship",
    "update",
    "work",
}

PRONOUNS = {"this", "that", "it", "they", "these", "those", "the", "there"}

NEEDS_WORDS = {"need", "needs", "should", "must", "ensure", "required", "require", "plan"}
REQUEST_STARTERS = ("please", "let's", "lets")
INTENT_WORDS = {"want", "plan", "intend", "aim", "hope", "prepare"}
INTENT_PHRASES = ("want to", "plan to", "intend to", "aim to", "hope to", "prepare to")

FIRST_PERSON_PRONOUNS = {
    "i",
    "i'm",
    "i’d",
    "i'd",
    "i’ll",
    "i'll",
    "i’ve",
    "i've",
    "me",
    "my",
    "mine",
    "myself",
    "we",
    "we're",
    "we’re",
    "we’ve",
    "we've",
    "we’ll",
    "we'll",
    "us",
    "our",
    "ours",
    "ourselves",
}

_nlp = None
_openai_client = None

load_dotenv()


def _get_nlp():
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_md")
        except OSError:
            logger.warning(
                "Falling back to spaCy 'en_core_web_sm'. "
                "Install 'en_core_web_md' for better keyword extraction."
            )
            _nlp = spacy.load("en_core_web_sm")
    return _nlp


def _clean_transcript(transcript: str | Iterable[str]) -> str:
    if isinstance(transcript, (list, tuple)):
        transcript = "".join(str(item) for item in transcript)
    return transcript.replace("\n", " ").strip()


def _sentence_relevance(sentence: Span, action: str) -> float:
    if not sentence or not sentence.text.strip():
        return 0.0

    tokens = list(sentence)
    text_lower = sentence.text.lower()

    if tokens and tokens[0].text.lower() in {"and", "but"}:
        base_penalty = 0.2
    else:
        base_penalty = 0.0

    has_modal = any(tok.tag_ == "MD" for tok in tokens)
    has_future_aux = any(
        tok.lower_ in {"will", "shall"} and tok.dep_ in {"aux", "auxpass"} for tok in tokens
    )
    has_need = any(tok.lemma_.lower() in NEEDS_WORDS for tok in tokens)
    starts_with_request = text_lower.startswith(REQUEST_STARTERS)
    has_request = starts_with_request or any(starter in text_lower for starter in REQUEST_STARTERS)
    has_follow = "follow up" in text_lower or "follow-up" in text_lower
    has_going_to = "going to" in text_lower or "gonna" in text_lower
    has_working_on = "working on" in text_lower or "work on" in text_lower
    has_intent = any(tok.lemma_.lower() in INTENT_WORDS for tok in tokens) or any(
        phrase in text_lower for phrase in INTENT_PHRASES
    )

    has_first_person = any(tok.lemma_.lower() in FIRST_PERSON_PRONOUNS for tok in tokens)
    root = sentence.root
    root_tense = set(root.morph.get("Tense"))

    score = 0.0
    if has_modal:
        score += 1.6
    if has_future_aux:
        score += 0.8
    if has_going_to:
        score += 1.0
    if has_need:
        score += 1.2
    if starts_with_request:
        score += 1.0
    elif has_request:
        score += 0.8
    if has_follow:
        score += 0.8
    if has_working_on:
        score += 0.7
    if has_intent:
        score += 1.0
    if any(tok.dep_ in {"dobj", "pobj", "attr", "oprd"} for tok in tokens):
        score += 0.4
    if any(tok.pos_ == "PROPN" for tok in tokens):
        score += 0.3
    if len(tokens) >= 12:
        score += 0.2
    if len(tokens) <= 5:
        score -= 0.6

    if has_first_person:
        if "Past" in root_tense and not (has_modal or has_need or has_going_to or has_intent):
            score -= 1.6
        elif not (has_modal or has_need or has_follow or has_going_to or has_working_on or has_intent):
            score -= 0.6
        else:
            score -= 0.2

    if action == "update":
        if "just want to update" in text_lower:
            score -= 2.0
        elif "want to update" in text_lower:
            score -= 1.0
        if not (has_need or has_modal or has_going_to or has_intent):
            score -= 0.6

    if action == "review" and has_first_person and not (has_follow or has_need or has_intent):
        score += 0.6

    if action == "follow" and not has_follow:
        score -= 0.4

    if action == "work" and not has_working_on:
        score -= 0.3

    if action == "finalize" and "finalize" not in text_lower and "finalise" not in text_lower:
        score -= 0.3

    if action == "send" and "send" not in text_lower:
        score -= 0.3

    if action == "schedule" and "schedule" not in text_lower and "scheduling" not in text_lower:
        score -= 0.3
    if action == "schedule" and ("let's" in text_lower or "lets" in text_lower):
        score += 1.0

    if action == "review" and "review" not in text_lower:
        score -= 0.3

    if action == "fix" and "fix" not in text_lower:
        score -= 0.3

    if action == "follow" and "follow" not in text_lower:
        score -= 0.3

    if action == "decide" and "decide" not in text_lower:
        score -= 0.3

    if action == "assign" and "assign" not in text_lower:
        score -= 0.3

    if action == "draft" and "draft" not in text_lower:
        score -= 0.3

    if action == "ship" and "ship" not in text_lower:
        score -= 0.3

    if action == "migrate" and "migrate" not in text_lower:
        score -= 0.3

    if action == "collaborate" and "collaborat" not in text_lower:
        score -= 0.3

    if action == "present" and "present" not in text_lower:
        score -= 0.3

    score -= base_penalty
    return score


def meeting_bulletpoints(transcript: str | Iterable[str]) -> dict[str, list[str]]:
    cleaned = _clean_transcript(transcript)

    if not cleaned:
        return {}

    doc = _get_nlp()(cleaned)
    sentences = list(doc.sents)
    trigger_words: dict[str, list[str]] = defaultdict(list)

    for idx, sentence in enumerate(sentences):
        verb_lemmas = {token.lemma_.lower() for token in sentence if token.pos_ == "VERB"}
        action_hits = verb_lemmas.intersection(ACTION_VERBS)
        if not action_hits:
            continue

        pronoun_lemmas = {
            token.lemma_.lower() for token in sentence if token.pos_ == "PRON"
        }
        pronoun_hits = pronoun_lemmas.intersection(PRONOUNS)

        targeted_sentence = sentence.text.strip()
        if pronoun_hits and idx > 0:
            targeted_sentence = sentences[idx - 1].text_with_ws + targeted_sentence

        for action in action_hits:
            relevance = _sentence_relevance(sentence, action)
            if pronoun_hits and idx > 0:
                relevance += 0.4 * _sentence_relevance(sentences[idx - 1], action)

            text_lower = targeted_sentence.lower()
            if "just want to update" in text_lower or "just wanted to update" in text_lower:
                continue

            if relevance < 0.5:
                continue

            trigger_words[action].append(targeted_sentence)

    return dict(trigger_words)


def _uses_first_person(text: str) -> bool:
    normalized = text.lower().replace("’", "'")
    tokens = [tok for tok in re.split(r"[^a-z']+", normalized) if tok]
    return any(tok in FIRST_PERSON_PRONOUNS for tok in tokens)


def _get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPEN_AI_KEY")
        if not api_key:
            raise RuntimeError("OPEN_AI_KEY is not set in the environment.")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def meeting_summary(transcript: str | Iterable[str], *, model: str = "gpt-4o-mini") -> str:
    cleaned = _clean_transcript(transcript)
    if not cleaned:
        return ""

    client = _get_openai_client()

    def _generate(request: str) -> str:
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert meeting summarizer. Your responses must be "
                        "written in third-person and must not contain any first-person pronouns."
                    ),
                },
                {"role": "user", "content": request},
            ],
        )
        return response.output_text.strip()

    prompt = (
        "Summarize the meeting transcript below.\n\n"
        "Requirements:\n"
        "- 4 to 6 sentences.\n"
        "- Third-person, objective tone.\n"
        "- No first-person pronouns (I, we, my, our, etc.).\n"
        "- No direct quotes.\n\n"
        f"Transcript:\n{cleaned}"
    )

    summary = _generate(prompt)

    if _uses_first_person(summary):
        logger.info("Retrying summary generation to remove first-person phrasing.")
        retry_prompt = (
            "Rewrite the following summary so that it uses third-person, objective language "
            "and removes every first-person pronoun. Preserve the meaning.\n\n"
            f"Summary:\n{summary}\n\n"
            f"Original transcript:\n{cleaned}"
        )
        summary = _generate(retry_prompt)

    return summary


if __name__ == "__main__":

    input_string = ""

    try:
        with open("test.txt", "r") as file:
            lines = file.readlines()

            for line in lines:
                input_string = input_string + line.strip() + " "

    except FileNotFoundError:
        print("Error: The file was not found.")

    print("Bullet points:", meeting_bulletpoints(input_string))
    print("\nSummary:\n", meeting_summary(input_string))
