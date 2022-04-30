import sys

import requests


class MWDictionary:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def lookup_word(self, word):
        """Looks up a word in the dictionary, returning a card with the word itself,
        as well as its definition and pronunciation."""
        api_request = 'https://www.dictionaryapi.com/api/v3/references/learners/json/' + word + '?key=' + self.api_key

        print('Looking up word: ' + word + '... ')
        response = requests.get(api_request)

        if response.status_code != 200:
            print('\nError when querying Merriam-Webster\'s Dictionary API.')
        elif 'Invalid API key' in response.text:
            print('Invalid API key. Make sure it is subscribed to Merriam Websters Learners Dictionary.\n'
                  'You can replace the current key by providing the argument [-k KEY].\n'
                  'Exiting...')
            sys.exit()

        response = response.json()[0]
        try:
            # Take the interesting parts of the response
            word_stem = response['meta']['stems'][0]
            definitions = response['shortdef']
            ipa = self.get_pronunciation(response)
            print('OK')
            return word_stem, definitions, ipa
        except KeyError as err:
            # Sometimes the response doesn't have the format we expected, will have to handle these edge cases as they
            # become known.
            print(f'Response wasn\'t in the expected format. Reason: key {str(err)} not found')
            raise
        except TypeError:
            # If the response isn't a dictionary, it means we get a list of suggested words so looking up keys won't
            # work.
            print(word + ' not found in Merriam-Webster\'s Learner\'s dictionary!')
            raise

    @staticmethod
    def get_pronunciation(response):
        """Return pronunciation from response."""
        # Where to find the pronunciation differs from word to word
        prs = response['hwi'].get('prs', None)
        altprs = response['hwi'].get('altprs', None)

        ipa = None
        if prs is not None:
            # Prefer to use prs
            ipa = prs[0]['ipa']
        elif altprs is not None:
            ipa = altprs[0]['ipa']

        if altprs is None and prs is None:
            # Couldn't find it in "hwi", it sometimes is in "vrs"
            ipa = response['vrs'][0]['prs'][0]['ipa']

        return ipa