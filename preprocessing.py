""" preprocessing

NLP tasks

"""

import json, nltk, random, pickle, string
random.seed(23)
nltk.data.path.append("/home/<user>/nltk_data")
from nltk.stem.lancaster import LancasterStemmer
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from keras.utils import to_categorical
from textblob import TextBlob

class Preprocessing(object):
    
    @classmethod
    def clean_up_sentence(self, sentence):
        """ Split sentence into clean list of words

        :param sentence: pattern
        :return: [word]
        """
        # tokenize the pattern
        sentence_words = nltk.word_tokenize(sentence)
        # stem each word
        sentence_words =self._clean_sequence(sentence_words)
        return sentence_words

    # function to check and get the part of speech tag count of a words in a given sentence
    @staticmethod
    def _check_pos_tag(sent, flag):
        cnt = 0
        for word in sent:
            try:
                wiki = TextBlob(word)
                for tup in wiki.tags:
                    ppo = list(tup)[1]
                    if ppo in pos_family[flag]:
                        cnt += 1
            except:
                pass
        return cnt

    @staticmethod
    def _clean_sequence(seq):
        """ Stemming, remove stopwords and punctuation from input sequence

        :param seq: [word]
        :return: [word] - cleaned seq of words
        """
        stemmer = LancasterStemmer()
        with open("data/custom_stopwords.p", "rb") as f:
            stop_words = pickle.load(f)

        cleaned_seq = [stemmer.stem(w.lower()) for w in seq if w not in
                       stop_words and w not in string.punctuation]

        return cleaned_seq

    @classmethod
    def parse_training_data(self, path):
        """ Parse training data and create dictonary for app

        :param path: path to training data
        :return: [word], [class], [document]
        """
        words = []
        classes = []
        documents = []

        with open(path) as json_data:
            intents = json.load(json_data)

        # loop through each sentence in our intents patterns
        for intent in intents["intents"]:
            for pattern in intent["patterns"]:

                # tokenize each word in the sentence
                w = nltk.word_tokenize(pattern)

                # add to our words list
                words.extend(w)

                # add to documents in our corpus
                documents.append((w, intent["tag"]))

                # add to our classes list
                if intent["tag"] not in classes:
                    classes.append(intent["tag"])

        # stem and lower each word and remove duplicates
        words = self._clean_sequence(words)
        words = sorted(list(set(words)))

        # remove duplicates
        classes = sorted(list(set(classes)))

        return words, classes, documents
    
    @classmethod
    def create_datasets(self, words, classes, documents):
        """ Create train- & testset

        vectorizes dataset

        :param words: list of parsed words
        :param classes: list of parsed classes
        :param documents: list of parsed docs
        :return: Trainset, Testset
        """
        # create our training data
        training = []
        # create an empty array for our output
        output_empty = [0] * len(classes)

        # training set, bag of words for each sentence
        for doc in documents:
            # initialize our bag of words
            bag = [0] * len(words) # BUGFIX
            # list of tokenized words for the pattern
            pattern_words = doc[0]
            # stem each word
            pattern_words = self._clean_sequence(pattern_words)
            # create our bag of words array - BUGFIX
            for pw in pattern_words:
                for i, w in enumerate(words):
                    if w == pw:
                        bag[i] += 1

            # class index as label
            target_num = doc[1]

            training.append([bag, target_num])

        # shuffle our features and turn into np.array
        random.shuffle(training)
        training = np.array(training)

        # create train and test lists, dirty hack because of keras input specifics
        X = np.vstack(training[:, 0])
        y = training[:, 1]
        y = pd.get_dummies(y)
        y = y.values.argmax(1)
        y = to_categorical(y, len(classes))

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.10, random_state=23, shuffle=True)

        return (X_train, y_train), (X_test, y_test)
    
    @classmethod
    def additional_features(cls, words, classes, documents):
        """
        :param words: list of parsed words
        :param classes: list of parsed classes
        :param documents: list of parsed docs
        :return:    Word Count of the documents, 
                    Character Count of the documents,
                    Average Word Density of the documents,
                    Puncutation Count in the Complete Essay,
                    Upper Case Count in the Complete Essay,
                    Title Word Count in the Complete Essay,
                    Frequency distribution of Part of Speech Tags:(Noun Count, Verb Count, Adjective Count, Adverb Count, Pronoun Count
        """
        
        trainDF = pd.DataFrame()
        trainDF['patterns'] = listOfAllPatterns = [pattern[0] for pattern in documents]

        #Counts:do not include white space charcters
        trainDF['char_count'] = trainDF['patterns'].apply(lambda x: sum([*map(len, x)]))
        trainDF['word_count'] = trainDF['patterns'].apply(len)
        trainDF['word_density'] = trainDF['char_count'] / (trainDF['word_count'])
        
        #Punctuation count: number of punctuation marks in pattern
        puncs_in_string = lambda x: sum([1 for _ in list(x) if _ in string.punctuation])
        trainDF['punctuation_count'] = trainDF['patterns'].apply(lambda x: sum([*map(puncs_in_string, x)])) 

        #Title Word Count: number of words starting with uppercase letter
        trainDF['title_word_count'] = trainDF['patterns'].apply(lambda x: sum([*map(str.istitle, x)]))

        #Uppercase word count: number of words in all upper case 
        trainDF['uppercase_word_count'] = trainDF['patterns'].apply(lambda x: sum([*map(str.isupper, x)]))
        
        #Parts of Speach
        pos_family = {
            'noun' : ['NN','NNS','NNP','NNPS'],
            'pron' : ['PRP','PRP$','WP','WP$'],
            'verb' : ['VB','VBD','VBG','VBN','VBP','VBZ'],
            'adj' :  ['JJ','JJR','JJS'],
            'adv' : ['RB','RBR','RBS','WRB']
        }
        
        trainDF['noun_count'] = trainDF['patterns'].apply(lambda x:cls._check_pos_tag(x, 'noun'))
        trainDF['verb_count'] = trainDF['patterns'].apply(lambda x:cls._check_pos_tag(x, 'verb'))
        trainDF['adj_count']  = trainDF['patterns'].apply(lambda x:cls._check_pos_tag(x, 'adj' ))
        trainDF['adv_count']  = trainDF['patterns'].apply(lambda x:cls._check_pos_tag(x, 'adv' ))
        trainDF['pron_count'] = trainDF['patterns'].apply(lambda x:cls._check_pos_tag(x, 'pron'))
        
        return trainDF

    @classmethod
    def bow(cls, sentence, words, show_details=False):
        """ Creates BoW

        :param sentence: pattern
        :param words: words list
        :param show_details:
        :return:
        """
        # tokenize the pattern
        sentence_words = cls.clean_up_sentence(sentence)
        # bag of words
        bag = [0]*len(words)
        for s in sentence_words:
            for i,w in enumerate(words):
                if w == s:
                    bag[i] += 1
                    if show_details:
                        print ("found in bag: %s" % w)

        return (np.array(bag))
