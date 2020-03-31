import gensim
import gensim.downloader as api

from torchtext.vocab import GloVe


import os
import torchtext_sentiment
import preprocessing

# INPUTS
############

CREATE_EMBEDDINGS = True
PROCESS_DATASETS = False
TRAINING_MODULE = False

# TODO CREATE OWN EMBEDDINGS
if CREATE_EMBEDDINGS:
    glove_vec = GloVe(name="6B", dim=100)
    glove_vec.save('glove_6B_100.kv')

    wv = api.load('word2vec-google-news-300')  # DOWNLOAD WORD VECTORS
    wv.save('word2vec_google_news_300.kv')  # SAVE WORD VECTORS LOCALLY
# TODO TEST EMBEDDINGS AND PLOT RESULTS

if PROCESS_DATASETS:
    dataset_path = os.getcwd()
    dataset_path = os.path.join(dataset_path, "data")
    dataset_path = os.path.join(dataset_path, "training.1600000.processed.noemoticon.csv")
    preprocessing.preprocess_text(dataset_path)

# TODO WRITE A LOOP FOR DIFFERENT CASES

N_EPOCHS = 10
param_grid = [
  {'MAX_VOCAB_SIZE': [10e3, 25e3],
   'min_freq': [1, 10],
   'freeze_embeddings': [True, False],
   'pretrained': [True],
   'vectors': ['glove_6B_100', 'word2vec_google_news_300']},
  {'MAX_VOCAB_SIZE': [10e3, 25e3],
   'min_freq': [1, 10],
    'freeze_embeddings': [True, False],
   'pretrained': [False],
   'vectors': [None]}]

i = 0
if TRAINING_MODULE:
    for param in param_grid:
        print(f"params {param}")
        for MAX_VOCAB_SIZE in param['MAX_VOCAB_SIZE']:
            for min_freq in param['min_freq']:
                for freeze_embeddings in param['freeze_embeddings']:
                    for pretrained in param['pretrained']:
                        for vectors in param['vectors']:
                            if vectors == None:
                                model_name = f"own_{MAX_VOCAB_SIZE}_{min_freq}_freeze_{freeze_embeddings}"
                            else:
                                model_name = f"{vectors}_{MAX_VOCAB_SIZE}_{min_freq}_freeze_{freeze_embeddings}"

                            print(f"{i}. Testing {model_name}")
                            print(f"MAX_VOCAB_SIZE {MAX_VOCAB_SIZE},"
                                  f"min_freq {min_freq},"
                                  f"pretrained {pretrained},"
                                  f"freeze_embeddings {freeze_embeddings}")

                            """
                            test_loss, test_acc = torchtext_sentiment.analyse_sentiments(MAX_VOCAB_SIZE=MAX_VOCAB_SIZE,
                                                                                         min_freq=min_freq,
                                                                                         pretrained=pretrained,
                                                                                         vectors=vectors,
                                                                                         freeze_embeddings=freeze_embeddings,
                                                                                         N_EPOCHS=N_EPOCHS,
                                                                                         model_name=model_name)
                            
                            print(f'Test Loss: {test_loss:.3f} | Test Acc: {test_acc * 100:.2f}%')
                            
                            """
                            i += 1

# TODO DO TESTS AND PLOT RESULTS