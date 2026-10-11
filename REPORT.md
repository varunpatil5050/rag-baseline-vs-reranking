# RAG baseline retrieval and reranking

Cross-Encoder reranking restored decisive evidence for three selected questions that baseline retrieval could not answer from its first three chunks. The experiment uses NIST SP 800-63B-4, Digital Identity Guidelines: Authentication and Authenticator Management, final July 2025 [1]. Two controls show why an improved rank need not improve an answer, and why missing candidates limit reranking.

Repository: [github.com/varunpatil5050/rag-baseline-vs-reranking](https://github.com/varunpatil5050/rag-baseline-vs-reranking)

## 1 Architecture comparison

The 129-page PDF yields 409 chunks from PDF pages 12-129, after excluding front matter. Each page is divided into 180-token windows with 40-token overlap. Both pipelines use this same corpus. The Bi-Encoder, sentence-transformers/all-MiniLM-L6-v2, embeds chunks and queries independently [2]. Chunk embeddings are precomputed. Both query and chunk vectors are normalized, so exact FAISS inner-product search is equivalent to cosine similarity.

Baseline retrieval returns ten candidates and supplies its first three to Gemini. The Cross-Encoder, cross-encoder/ms-marco-MiniLM-L6-v2, jointly processes every one of the same ten query-chunk pairs, allowing self-attention across their tokens [3, 4]. It sorts candidates by descending relevance score and supplies the new first three. These relevance scores are not probabilities or cosine similarities.

Both answers use gemini-3.8-flash, temperature 0, seed 42, and the same prompt template [5]. Only the three selected excerpts change. The prompt requires evidence-based answers, chunk citations, and acknowledgement of missing information; generation settings do not guarantee deterministic responses.

## 2 Qualitative and rank shift analysis

The five cases were selected from 44 exploratory queries. The three recoveries below were checked against the full baseline context for equivalent evidence. They are selected stress tests, not an estimate of average accuracy. The paired answers are reproduced in full.

### D10 Resetting failed attempts

**Question:** When a user requests a fresh out-of-band verification code, can the failed-attempt counter start over?

PDF page 33 (printed 22), section 3.1.3.2. Chunk p033_c03: rank 4 to 1.

**Answer 1 baseline**

The provided excerpts do not establish whether a failed-attempt counter can start over when a user requests a fresh out-of-band verification code. The excerpts discuss out-of-band authenticators and recovery code requirements, including validity periods, format, and throttling under Sec. 3.2.2 [p059_c03, p031_c04, p059_c02], but they completely lack any mention of a failed-attempt counter or the conditions under which it may be reset.

**Answer 2 reranked**

No. Generating a new authentication secret SHALL NOT reset the failed authentication count [p033_c02, p033_c03].

Baseline retrieved recovery-code material instead of the out-of-band counter restriction. The reranked context restores that restriction. The improvement is from an explicit abstention to a supported answer, not correction of a fabricated reset rule.

### D28 Reusing biometric samples

**Question:** Can face images collected during sign-in be reused to improve the matching template or for research, and what permission is needed?

PDF page 45 (printed 34), section 3.2.3.4. Chunk p045_c01: rank 5 to 2.

**Answer 1 baseline**

The provided excerpts do not establish whether face images collected during sign-in can be reused to improve the matching template or for research, nor do they establish what permission is needed.

The excerpts only state that facial images do not constitute secrets and can often be obtained without consent [p043_c01], detail usability considerations that affect facial recognition accuracy (e.g., artifacts, lighting, expressions, poses) [p089_c01], and define central comparison requirements—including that sensors/endpoints SHALL be authenticated, appropriate controls SHALL be implemented for sensitive personal information, and verifiers MAY limit centrally stored templates to particular sensors [p044_c04]. Any provisions regarding the reuse of sign-in biometric samples or required permissions are missing.

**Answer 2 reranked**

Biometric samples collected during the authentication process MAY be used locally within the authenticator or verifier performing the biometric comparison to update templates (to compensate for changes in subscriber characteristics) or for other research purposes [p045_c01].

Regarding permission:

* For research purposes, "explicit subscriber consent" is required [p045_c01].
* For updating templates to compensate for changes in subscriber characteristics, the text does not state that permission is needed [p045_c01].

Additionally, the samples and any derived biometric data SHALL be erased immediately after adaptation or research data has been derived, and an allowable time limit for adaptation SHALL be established and enforced by the authenticator or CSP [p045_c01].

Baseline lacked the permission and consent clause. Reranking retrieves the local-use rule and the explicit-consent condition for other research. The cited provision does not state that template adaptation requires consent; this does not establish an exemption from all other applicable consent requirements.

### D34 Sending a postal recovery notice

**Question:** If the only electronic notification address was also used to receive a recovery code, can the provider skip sending a postal recovery notice?

PDF page 63 (printed 52), section 4.6. Chunk p063_c02: rank 6 to 1.

**Answer 1 baseline**

The provided excerpts do not establish the answer. They do not contain any information or requirements regarding postal recovery notices, nor do they state whether a provider can skip sending a postal recovery notice if the only electronic notification address was used to receive a recovery code [p059_c02, p059_c03, p060_c01].

**Answer 2 reranked**

No, the provider cannot skip sending a postal recovery notice [p063_c02].

According to the excerpt, account recovery notifications SHALL also be sent to a postal address if the only other notification address in the subscriber account is the address to which an issued recovery code was sent [p063_c02].

The baseline evidence covers recovery-code delivery, not the notification exception. Reranking restores the separate obligation to send a postal notice when the only other notification address received the issued recovery code.

### Controls and retrieval limits

D03 asks whether cloud-synced passkeys can satisfy AAL3. The designated prohibition, p020_c01 (PDF 20, printed 9, section 2.3.2), moves from rank 4 to 2. However, baseline rank 2 already contains equivalent evidence in p103_c02 (PDF 103, printed 92). Both answers correctly reject synced passkeys at AAL3, so this is not a failure recovery.

D05 asks whether voice biometrics may be used. The prohibition in p043_c04 (PDF 43, printed 32, section 3.2.3.2) is absent from the original ten candidates. Baseline incorrectly permits voice biometrics under general biometric conditions; the reranked answer abstains. Abstention avoids the unsupported permission, but the missing rule is not recovered. Full control answers and all candidate lists are retained in the notebook and results.

## 3 Latency profiling

Each query has one warm-up and seven measured repetitions, giving 35 samples. The run uses Python 3.12.3 on an ARM64 Mac with macOS 26.6.2, CPU inference, and one thread each for Torch and FAISS. The table reports medians in milliseconds from results/latency_summary.csv.

| Case | Baseline median ms | Reranking increment median ms | Advanced total median ms | Total / baseline |
|---|---:|---:|---:|---:|
| D10 | 4.70 | 127.72 | 132.14 | 28.11x |
| D28 | 4.76 | 125.96 | 130.72 | 27.46x |
| D34 | 4.64 | 125.72 | 130.52 | 28.16x |
| D03 | 4.68 | 124.72 | 129.50 | 27.69x |
| D05 | 4.85 | 133.90 | 138.65 | 28.60x |

Baseline includes query embedding, vector search, and candidate construction. Incremental reranking includes pair validation, tokenization, inference, sorting, and result construction. Advanced total adds both stages within each repetition; separately computed medians need not add exactly. Model loading, PDF processing, indexing, and Gemini generation are excluded.

Advanced retrieval is about 27.5-28.6 times slower in these measurements. Seven samples provide limited precision. The latest run recomputed retrieval and timings but reused all ten earlier Gemini responses from an exact prompt/model/configuration cache; it generated no new API answers. Original response timestamps remain in results/answers.json.

## 4 Why reranking follows retrieval

A Cross-Encoder must jointly process each query with each candidate chunk. Applying it first would require 409 pairs here rather than ten: 40.9 times as many pairs, not a measured 40.9-fold latency increase. Bi-Encoder document vectors can be reused across queries, and the vector store narrows expensive joint scoring to ten candidates. This implementation uses exact FAISS search, not approximate search. Larger collections make the difference in pair counts grow, while D05 shows the cost of an initial retrieval miss. Reranking improves selection only within the candidates it receives.

### References

[[1] NIST SP 800-63B-4 final publication](https://csrc.nist.gov/pubs/sp/800/63/b/4/final)

[[2] all-MiniLM-L6-v2 model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)

[[3] MS MARCO MiniLM Cross-Encoder model card](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2)

[[4] Sentence Transformers Cross-Encoder documentation](https://www.sbert.net/docs/cross_encoder/usage/usage.html)

[[5] Gemini content generation documentation](https://ai.google.dev/gemini-api/docs/generate-content)
