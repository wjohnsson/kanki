import logging
import sys
from typing import List, Tuple, NoReturn, Optional

import requests


class MWDictionary:
    """
    A wrapper for a subset of the Merriam-Websters Learner's dictionary API.

    API documentation https://dictionaryapi.com/products/json
    """
    api_base_url = 'https://www.dictionaryapi.com/api/v3/references/learners/json/'
    max_queries = 1000  # amount of free lookups allowed per day

    def __init__(self, api_key: str):
        self.api_key = api_key

    def lookup(self, word: str) -> Tuple[str, List[str], str]:
        """Looks up a word in the dictionary, returning the word itself, its definition and pronunciation."""
        api_request = self.api_base_url + word + '?key=' + self.api_key

        logging.info('Looking up word: ' + word)
        response = requests.get(api_request)

        self.check_response(response)

        dict_entry = response.json()[0]
        try:
            # Take the interesting parts of the response
            word_stem = self.get_word_stem(dict_entry)
            definitions = self.get_word_definition(dict_entry)
            ipa = self.get_pronunciation(dict_entry)
            print('OK')
            return word_stem, definitions, ipa
        except KeyError as err:
            # Sometimes the response doesn't have the format we expected, will have to handle these edge cases as they
            # become known.
            logging.warning(f'API response wasn\'t in the expected format. Reason: key {str(err)} not found')
            print(f'bad API response')
            raise
        except TypeError:
            # If the response isn't a dictionary, it means we get a list of suggested words so looking up keys won't
            # work.
            print(f'not found in Merriam-Webster\'s Learner\'s dictionary!')
            raise

    @staticmethod
    def check_response(response: requests.Response) -> NoReturn:
        if response.status_code != 200:
            logging.error('Unable to query Merriam-Webster\'s Dictionary API.')
        elif 'Invalid API key' in response.text:
            api_key = response.request.url.split('?key=')[-1]
            logging.error(f'Invalid API key: {api_key}')
            print('Make sure your API key is subscribed to Merriam Websters Learner\'s Dictionary.\n'
                  'You can replace the current key by providing the argument [-k KEY].')
            print('Exiting...')
            sys.exit(1)

    @staticmethod
    def get_word_definition(entry: dict) -> List[str]:
        return entry['shortdef']

    @staticmethod
    def get_word_stem(entry: dict) -> str:
        return entry['meta']['stems'][0]

    @staticmethod
    def get_pronunciation(entry: dict) -> Optional[str]:
        """Maybe return word pronunciation from API response."""
        headword_information = 'hwi'
        pronunciations = 'prs'
        phonetic_alphabet = 'ipa'  # International Phonetic Alphabet pronunciation
        variants = 'vrs'
        alternative_pronunciations = 'altprs'

        # Where to find the pronunciations can differ from word to word
        prs = entry[headword_information].get(pronunciations, None)
        if prs:
            return prs[0][phonetic_alphabet]

        # If there is no pronunciation suitable for print, we might find the one for electronic display
        altprs = entry[headword_information].get(alternative_pronunciations, None)
        if altprs:
            return altprs[0][phonetic_alphabet]

        # Couldn't find it in headword information, sometimes it is in one of the Variants
        vrs = entry[variants][0]
        variant_pronunciation = vrs[pronunciations][0].get(phonetic_alphabet, None)
        if not variant_pronunciation:
            print('Couldn\'t find pronunciation')
        return variant_pronunciation
