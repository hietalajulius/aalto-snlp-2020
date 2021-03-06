from sklearn.metrics import confusion_matrix
import time
import torch
import torch.nn as nn
import torch.optim as optim
import torchtext
import torchtext.vocab
from torchtext.data import TabularDataset

from embeddings import load_vectors
from utils import epoch_time
from gru import RNNModel

import os
from preprocessing import preprocess
import numpy as np
from nltk.corpus import stopwords

import matplotlib.pyplot as plt
plt.switch_backend('agg')
import itertools


def binary_accuracy(preds, y):
    """
    Returns accuracy per batch, i.e. if you get 8/10 right, this returns 0.8, NOT 8
    """

    # round predictions to the closest integer
    rounded_preds = torch.round(torch.sigmoid(preds))
    correct = (rounded_preds == y).float()  # convert into float for division
    acc = correct.sum() / len(correct)

    return acc


def plot_confusion_matrix(cm, classes, normalize=False, title='Confusion matrix', show_plot=True, fname=None):
    """

    :param cm:
    :param classes:
    :param normalize:
    :param title:
    :param show_plot:
    :param fname:
    :return:
    """


    cmap = plt.cm.Blues
    if normalize:
        cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
        print("Normalized confusion matrix")
    else:
        print('Confusion matrix, without normalization')

    print(cm)
    if show_plot:
        plt.imshow(cm, interpolation='nearest', cmap=cmap)
        plt.title(title)
        plt.colorbar()
        tick_marks = np.arange(len(classes))
        plt.xticks(tick_marks, classes, rotation=45)
        plt.yticks(tick_marks, classes)

        fmt = '.2f' if normalize else 'd'
        thresh = cm.max() / 2.
        for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
            plt.text(j, i, format(cm[i, j], fmt), horizontalalignment="center", color="white" if cm[i, j] > thresh else "black")

        plt.tight_layout()
        plt.ylabel('True label')
        plt.xlabel('Predicted label')

        fpath = os.path.normpath(os.getcwd() + os.sep + os.pardir)
        fpath = os.path.join(fpath, "data")
        fname = 'cm_' + fname
        fpath = os.path.join(fpath, fname)
        print(f"fpath is {fpath}")
        plt.savefig(filename=fpath)

        # plt.show()


def confusion_matrix(model, iterator, device, fname):
    """

    :param model:
    :param iterator:
    :param device:
    :return:
    """
    predlist = torch.tensor([])
    lbllist = torch.tensor([])
    with torch.no_grad():
        for i, batch in enumerate(iterator):
            if batch.SentimentText.nelement() > 0:
                inputs = batch.SentimentText.to(device)
                classes = batch.Sentiment.to(device)
                text_lengths = [len(seq) for seq in batch.SentimentText]
                outputs = model(inputs, text_lengths).squeeze(1)
                # print(f"outputs.shape {outputs.shape}")
                # print(outputs)
                # Append batch prediction results
                # print(f"outputs.view(-1) {outputs.view(-1)}")
                # print(f"classes.view(-1) {classes.view(-1)}")
                # print(f"torch.sigmoid(outputs.view(-1))) {torch.sigmoid(outputs.view(-1))}")
                # print(f" torch.round(torch.sigmoid(outputs.view(-1))) {torch.round(torch.sigmoid(outputs.view(-1)))}")
                predlist = torch.cat([predlist, torch.round(torch.sigmoid(outputs.view(-1))).cpu()])
                lbllist = torch.cat([lbllist, classes.view(-1).cpu()])
                #print(f"predlist.shape {predlist.shape}")
                #print(f"lbllist.shape {lbllist.shape}")

    stacked = torch.stack((lbllist, predlist), dim=1)
    # print(f"stacked {stacked.shape}")
    cmt = torch.zeros(2, 2, dtype=torch.int64)
    for p in stacked:
        # print(f"p is {p}")
        tl, pl = p.tolist()
        # print(f"tl is {tl}, pl is {pl}")
        cmt[int(tl), int(pl)] = cmt[int(tl), int(pl)] + 1

    # print(f"cm is {cmt.shape} {cmt}")
    classes = ('Negative', 'Positive')
    plot_confusion_matrix(cmt.numpy(), classes, normalize=True, title='Confusion matrix', fname=fname)

def evaluate(model, iterator, criterion):
    """

    :param model:
    :param iterator:
    :param criterion:
    :return:
    """
    epoch_loss = 0
    epoch_acc = 0

    model.eval()
    with torch.no_grad():
        for batch in iterator:
            # print(batch.SentimentText)
            if batch.SentimentText.nelement() > 0:

                text_lengths = [len(seq) for seq in batch.SentimentText]
                predictions = model(batch.SentimentText, text_lengths).squeeze(1)

                loss = criterion(predictions, batch.Sentiment)

                acc = binary_accuracy(predictions, batch.Sentiment)

                epoch_loss += loss.item()
                epoch_acc += acc.item()

            # else:
            # print(f"Found a non-empty Tensorlist {batch.SentimentText}")

    return epoch_loss / len(iterator), epoch_acc / len(iterator)


def evaluate_sentences(model, sentence, TEXT, device):
    """

    :param model:
    :param sentence:
    :param TEXT:
    :param device:
    :return:
    """

    stop_words = set(stopwords.words('english'))
    model.eval()
    tokenized = preprocess(sentence, stop_words, stem=False, stemmer=None)
    # print(f"tokenized {tokenized}")
    indexed = [TEXT.vocab.stoi[t] for t in tokenized]
    length = [len(indexed)]
    length_tensor = torch.LongTensor(length)
    tensor = torch.LongTensor(indexed).to(device)
    # print(f"tensor {tensor.shape} length {length}")
    tensor = tensor.unsqueeze(0)
    print(f"model output before sigmoid {model(tensor, length_tensor)}")
    prediction = torch.sigmoid(model(tensor, length_tensor))
    return prediction.item()


def train_epoch(model, iterator, optimizer, criterion, device):
    epoch_loss = 0
    epoch_acc = 0

    model.train()
    #
    for text, y in iterator:
        optimizer.zero_grad()

        # print(f"text is {text}")
        # print(f"text.shape is {text.shape}")
        text_lengths = [len(seq) for seq in text]
        # print(f"text_lengths is {text_lengths}")
        predictions = model(text, text_lengths).squeeze(1)
        # predictions = model(batch.SentimentText).squeeze(1)
        loss = criterion(predictions, y)
        acc = binary_accuracy(predictions, y)

        loss.backward()
        optimizer.step()

        epoch_loss += loss.item()
        epoch_acc += acc.item()

    return model, epoch_loss / len(iterator), epoch_acc / len(iterator)


def analyse_sentiments(params=None,
                       model_name='',
                       training_mode=True):
    """

    :param params:
    :param model_name:
    :return:
    """

    vector_name = params['pretrained_vectors']
    MAX_VOCAB_SIZE = params['MAX_VOCAB_SIZE']
    min_freq = params['min_freq']
    EMBEDDING_DIM = params['embedding_dim']

    FREEZE_EMDEDDINGS = params['RNN_FREEZE_EMDEDDINGS']
    HIDDEN_DIM = params['RNN_HIDDEN_DIM']  # model_params['RNN_HIDDEN_DIM']
    OUTPUT_DIM = 1  # params['OUTPUT_DIM']
    N_LAYERS = params['RNN_N_LAYERS']   # model_params['RNN_N_LAYERS']
    DROPOUT = params['RNN_DROPOUT']   # model_params['RNN_DROPOUT']
    USE_GRU = params['RNN_USE_GRU']  # model_params['RNN_USE_GRU']
    N_EPOCHS = params['RNN_EPOCHS']
    BATCH_SIZE = params['RNN_BATCH_SIZE']

    pretrained = True
    if vector_name == None:
        pretrained = False


    TEXT = torchtext.data.Field(lower=True,
                                pad_first=True,
                                batch_first=True,
                                init_token='<sos>',
                                eos_token='<eos>'
                                # include_lengths=True
                                )

    LABEL = torchtext.data.LabelField(dtype=torch.float)
    datafields = [('Sentiment', LABEL), ('SentimentText', TEXT)]
    train_set, val_set, test_set = TabularDataset.splits(path='../data/',
                                    train='processed_train.csv',
                                    validation='processed_val.csv',
                                    test='processed_test.csv',
                                    format='csv',
                                    skip_header=True,
                                    fields=datafields)

    if pretrained:
        vectors = load_vectors(fname=vector_name)
        TEXT.build_vocab(train_set,
                         vectors=vectors,
                         unk_init=torch.Tensor.normal_)
        vectors = TEXT.vocab.vectors
        # print(vectors.shape)
        EMBEDDING_DIM = vectors.shape[1]
    else:
        TEXT.build_vocab(train_set,
                         max_size=MAX_VOCAB_SIZE)
    LABEL.build_vocab(train_set)
    print(f"Most frequent words in vocab. {TEXT.vocab.freqs.most_common(20)}")

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Device used is {device}")
    # minimise badding for each sentence
    train_iterator, val_iterator, test_iterator = torchtext.data.BucketIterator.splits(
                                                                        (train_set, val_set, test_set),
                                                                        batch_size=BATCH_SIZE,
                                                                        sort_key=lambda x: len(x.SentimentText),
                                                                        sort_within_batch=False,
                                                                        device=device)

    pad_idx = TEXT.vocab.stoi[TEXT.pad_token]
    INPUT_DIM = len(TEXT.vocab)
    print(f"Vocab size is {INPUT_DIM}, emdebbing dim is {EMBEDDING_DIM}")
    model = RNNModel(vocab_size=INPUT_DIM,
                    embedding_dim=EMBEDDING_DIM,
                    hidden_dim=HIDDEN_DIM,
                    output_dim=OUTPUT_DIM,
                    n_layers=N_LAYERS,
                    bidirectional=True,
                    dropout=DROPOUT,
                    pad_idx=pad_idx,
                    use_gru=USE_GRU)
    print(model)

    if pretrained:
        model.embedding.weight.data.copy_(vectors)

    unk_idx = TEXT.vocab.stoi[TEXT.unk_token]
    init_idx = TEXT.vocab.stoi[TEXT.init_token]
    eos_idx = TEXT.vocab.stoi[TEXT.eos_token]
    print(f"pad_idx {pad_idx}, unk_idx {unk_idx}, init_idx {init_idx}, eos_idx {eos_idx}")
    model.embedding.weight.data[unk_idx] = torch.zeros(EMBEDDING_DIM)
    model.embedding.weight.data[pad_idx] = torch.zeros(EMBEDDING_DIM)

    # freeze embeddings
    if FREEZE_EMDEDDINGS:
        model.embedding.weight.requires_grad = False
    else:
        model.embedding.weight.requires_grad = True

    optimizer = optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.BCEWithLogitsLoss()
    model = model.to(device)
    criterion = criterion.to(device)

    if training_mode:
        best_valid_loss = float('inf')
        for epoch in range(N_EPOCHS):
            start_time = time.time()
            model, train_loss, train_acc = train_epoch(model, train_iterator, optimizer, criterion, device)
            valid_loss, valid_acc = evaluate(model, val_iterator, criterion)
            end_time = time.time()

            epoch_mins, epoch_secs = epoch_time(start_time, end_time)

            if valid_loss < best_valid_loss:
                best_valid_loss = valid_loss
                torch.save(model.state_dict(), f"{model_name}.pt")

            print(f'Epoch: {epoch + 1:02} | Epoch Time: {epoch_mins}m {epoch_secs}s')
            print(f'\tTrain Loss: {train_loss:.3f} | Train Acc: {train_acc * 100:.2f}%')
            print(f'\t Val. Loss: {valid_loss:.3f} |  Val. Acc: {valid_acc * 100:.2f}%')

    # TODO DO TESTS AND PLOT RESULT
    # Evaluate model performance
    model.load_state_dict(torch.load(f"{model_name}.pt"))
    # print(model)

    test_loss, test_acc = evaluate(model, test_iterator, criterion)
    print(f'Test Loss: {test_loss:.3f} | Test Acc: {test_acc * 100:.2f}%')

    confusion_matrix(model, test_iterator, device=device, fname=model_name)

    sentence = "got a whole new wave of depression when i saw it was my rafa's losing match  I HATE YOU SODERLING"
    value = evaluate_sentences(model, sentence, TEXT, device)
    print(f"'{sentence}' sentiment is {value}")

    sentence = "STOKED for the show tomorrow night! 2 great shows combined."
    value = evaluate_sentences(model, sentence, TEXT, device)
    print(f"'{sentence}' sentiment is {value}")
    return test_loss, test_acc
