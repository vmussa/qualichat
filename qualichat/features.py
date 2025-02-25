'''
MIT License

Copyright (c) 2021 Qualichat

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

from typing import (
    List,
    DefaultDict,
    Callable,
    Any,
    Optional,
    Dict,
    Union,
    Set
)
from collections import defaultdict

import spacy
import matplotlib.pyplot as plt
import plotly.graph_objects as go # type: ignore
from pandas import DataFrame
from pandas.core.generic import NDFrame
from wordcloud import ( # type: ignore
    STOPWORDS,
    WordCloud
)
from plotly.subplots import make_subplots # type: ignore

from .chat import Chat
from .models import Message
from .enums import Period, SubPeriod, MessageType
from .utils import progress_bar


__all__ = (
    'generate_chart',
    'BaseFeature',
    'MessagesFeature',
    'TimeFeature',
    'NounsFeature',
    'VerbsFeature',
    'EmojisFeature',
)


def generate_chart(
    *,
    bars: Optional[List[str]] = None,
    lines: Optional[List[str]] = None,
    title: Optional[str] = None
):
    """A decorator that generates a chart automatically.

    Parameters
    ----------
    bars: Optional[List[:class:`str`]]
        The list of columns that will be interpreted as bars. Defaults
        to ``None``.
    lines: Optional[List[:class:`str`]]
        The list of columns that will be interpreted as lines. Defaults
        to ``None``.
    title: Optional[:class:`str`]
        The title of the chart. Defaults to ``None``.
    """
    if bars is None:
        bars = []

    if lines is None:
        lines = []

    def decorator(
        method: Callable[..., Union[DataFrame, NDFrame]]
    ) -> Callable[..., None]:
        def generator(
            self: BaseFeature,
            *args: Any,
            **kwargs: Any
        ) -> None:
            fig = make_subplots( # type: ignore
                specs=[[{'secondary_y': True}]]
            )
            dataframe = method(self, *args, **kwargs)

            index = dataframe.index # type: ignore

            if bars is not None:
                for bar in bars:
                    filtered = getattr(dataframe, bar)
                    fig.add_bar( # type: ignore
                        x=index,
                        y=list(filtered),
                        name=bar
                    )

            if lines is not None:
                for line in lines:
                    filtered = getattr(dataframe, line)
                    fig.add_trace( # type: ignore
                        go.Scatter( # type: ignore
                            x=index, y=list(filtered), name=line
                        ),
                        secondary_y=bool(bars),
                    )

            fig.update_layout(title_text=title) # type: ignore
            fig.show() # type: ignore

        # Dummy implementation for the decorated function to inherit
        # the documentation.
        generator.__doc__ = method.__doc__
        generator.__annotations__ = method.__annotations__

        return generator
    return decorator


stopwords: Set[str] = set(STOPWORDS) # type: ignore
stopwords.update(['da', 'meu', 'em', 'você', 'de', 'ao', 'os', 'eu'])


def generate_word_cloud(): # type: ignore
    """A decorator that generates a word cloud automatically."""
    def decorator(
        method: Callable[..., WordCloud] # type: ignore
    ) -> Callable[..., None]:
        def generator(self: BaseFeature, *args: Any, **kwargs: Any) -> None:
            wordcloud = method(self, *args, **kwargs) # type: ignore
            wordcloud.stopwords = stopwords

            plt.figure()
            plt.imshow(wordcloud, interpolation='bilinear') # type: ignore
            plt.axis('off')
            plt.show()

        # Dummy implementation for the decorated function to inherit
        # the documentation.
        generator.__doc__ = method.__doc__
        generator.__annotations__ = method.__annotations__

        return generator
    return decorator # type: ignore


def get_length(obj: List[str]) -> int:
    return len(''.join(obj))


WEEKDAYS = [
    'Sunday', 'Monday',
    'Tuesday', 'Wednesday',
    'Thursday', 'Friday',
    'Saturday'
]
PERIODS = [c.value for c in Period]
SUB_PERIODS = [c.value for c in SubPeriod]


class BaseFeature:
    """Represents the base of a Qualichat feature.
    Generally, you should use the built-in features that Qualichat
    offers you. However, you can subclass this class and create your
    own features.

    .. note::

        To automatically generate charts, you must create a method
        decorated with :meth:`generate_chart` that returns a
        :class:`pandas.DataFrame`.

    Attributes
    ----------
    chats: List[:class:`.Chat`]
        All the chats loaded via :meth:`qualichat.load_chats`.
    """

    __slots__ = ('chats',)

    def __init__(self, chats: List[Chat]) -> None:
        self.chats = chats


class MessagesFeature(BaseFeature):
    """A feature that adds charts generator related to chat messages.
    
    .. note::

        This feature is already automatically added to Qualichat.

    Attributes
    ----------
    chats: List[:class:`.Chat`]
        All the chats loaded via :meth:`qualichat.load_chats`.
    """

    __slots__ = ()

    @generate_chart(
        bars=['Qty_char_net', 'Qty_char_text'],
        lines=['Qty_messages'],
        title='Amount by Month'
    )
    def per_month(self) -> DataFrame:
        """Shows how many messages were sent per month."""
        chat = self.chats[0]
        data: DefaultDict[str, List[Message]] = defaultdict(list)

        columns = ['Qty_char_net', 'Qty_char_text', 'Qty_messages']
        rows: List[List[int]] = []

        for message in chat.messages:
            index = message.created_at.replace(
                day=1, hour=0, minute=0, second=0
            )
            data[index.strftime('%B %Y')].append(message)

        index = list(data.keys())

        for messages in data.values():
            net_content = 0
            pure_content = 0
            total_messages = 0

            for message in messages:
                net_content += len(message['Qty_char_net'])
                pure_content += len(message['Qty_char_text'])
                total_messages += 1

            rows.append([net_content, pure_content, total_messages])

        return DataFrame(rows, index=index, columns=columns)

    @generate_chart(
        bars=WEEKDAYS,
        lines=['Qty_char_net'],
        title='Amount by Month'
    )
    def weekdays_per_month(self) -> DataFrame:
        """Shows the amount of messages sent per week during the
        month.
        """
        chat = self.chats[0]
        data: DefaultDict[str, List[Message]] = defaultdict(list)

        columns = WEEKDAYS.copy()
        columns.append('Qty_char_net')
        rows: List[List[int]] = []

        for message in chat.messages:
            index = message.created_at.replace(hour=0, minute=0, second=0)
            data[index.strftime('%B %Y')].append(message)

        index = list(data.keys())

        for messages in data.values():
            weekdays = {w: 0 for w in WEEKDAYS}
            net_content = 0

            for message in messages:
                weekdays[message.created_at.strftime('%A')] += 1
                net_content += len(message['Qty_char_net'])

            rows.append([*weekdays.values(), net_content])

        return DataFrame(rows, index=index, columns=columns)

    @generate_chart(
        bars=['Qty_char_net', 'Qty_char_text'],
        lines=['Qty_messages'],
        title='Amount by Weekday'
    )
    def per_weekday(self) -> DataFrame:
        """Shows the amount of messages sent per week. The difference
        between this method and :meth:`.weekdays_per_month` is that
        this method groups every month.
        """
        chat = self.chats[0]
        data: Dict[str, List[Message]] = {w: [] for w in WEEKDAYS}

        columns = ['Qty_char_net', 'Qty_char_text', 'Qty_messages']
        rows: List[List[int]] = []

        for message in chat.messages:
            index = message.created_at.replace(hour=0, minute=0, second=0)
            data[index.strftime('%A')].append(message)

        index = list(data.keys())

        for messages in data.values():
            net_content = 0
            text_content = 0
            total_messages = 0

            for message in messages:
                net_content += len(message['Qty_char_net'])
                text_content += len(message['Qty_char_text'])
                total_messages += 1

            rows.append([net_content, text_content, total_messages])

        return DataFrame(rows, index=index, columns=columns)

    @generate_chart(
        bars=[
            'Qty_char_laughs', 'Qty_char_marks',
            'Qty_char_emoji', 'Qty_char_numbers'
        ],
        lines=['Qty_messages'],
        title='Amount by Month'
    )
    def fabrications(self) -> DataFrame:
        """Shows what are the most common fabrication aspects in
        messages per month.

        Fabrication aspects can be interpreted as:

        - Laughs
        - Marks
        - Emojis
        - Numbers
        
        And it will be compared with the total messages sent per month.
        """
        chat = self.chats[0]
        data: DefaultDict[str, List[Message]] = defaultdict(list)

        columns = [
            'Qty_char_laughs', 'Qty_char_marks',
            'Qty_char_emoji', 'Qty_char_numbers',
            'Qty_messages'
        ]
        rows: List[List[int]] = []

        for message in chat.messages:
            index = message.created_at.replace(
                day=1, hour=0, minute=0, second=0
            )
            data[index.strftime('%B %Y')].append(message)

        index = list(data.keys())

        for messages in data.values():
            laughs = 0
            marks = 0
            emojis = 0
            numbers = 0
            total_messages = 0

            for message in messages:
                laughs += get_length(message['Qty_char_laughs'])
                marks += get_length(message['Qty_char_marks'])
                emojis += get_length(message['Qty_char_emoji'])
                numbers += get_length(message['Qty_char_numbers'])
                total_messages += 1

            rows.append([laughs, marks, emojis, numbers, total_messages])

        return DataFrame(rows, index=index, columns=columns)

    @generate_chart(
        bars=['Qty_char_links', 'Qty_char_emails', 'Qty_char_mentions'],
        lines=['Qty_messages'],
        title='Amount by Month'
    )
    def laminations(self) -> DataFrame:
        """Shows what are the most common lamination aspects in
        messages per month.

        Lamination aspects can be interpreted as:

        - Links/URLs
        - E-mails
        - Mentions

        And it will be compared with the total messages sent per month.
        """
        chat = self.chats[0]
        data: DefaultDict[str, List[Message]] = defaultdict(list)

        columns = [
            'Qty_char_links', 'Qty_char_emails',
            'Qty_char_mentions', 'Qty_messages'
        ]
        rows: List[List[int]] = []

        for message in chat.messages:
            index = message.created_at.replace(hour=0, minute=0, second=0)
            data[index.strftime('%B %Y')].append(message)

        index = list(data.keys())

        for messages in data.values():
            links = 0
            emails = 0
            mentions = 0
            total_messages = 0

            for message in messages:
                links += get_length(message['Qty_char_links'])
                emails += get_length(message['Qty_char_emails'])
                mentions += get_length(message['Qty_char_mentions'])
                total_messages += 1

            rows.append([links, emails, mentions, total_messages])

        return DataFrame(rows, index=index, columns=columns)

    @generate_chart(
        bars=PERIODS,
        lines=['Qty_messages'],
        title='Amount by Month'
    )
    def by_periods(self) -> DataFrame:
        """Shows which periods of the day the chat is most active.
        
        Currently, the periods are:

        - Dawn
        - Morning
        - Evening
        - Night

        For more information, see :class:`.Period`.
        """
        chat = self.chats[0]
        data: DefaultDict[str, List[Message]] = defaultdict(list)

        columns = PERIODS.copy()
        columns.append('Qty_messages')

        rows: List[List[int]] = []

        for message in chat.messages:
            index = message.created_at.replace(
                day=1, hour=0, minute=0, second=0
            )
            data[index.strftime('%B %Y')].append(message)

        index = list(data.keys())

        for messages in data.values():
            periods = {v: 0 for v in PERIODS}
            total_messages = 0

            for message in messages:
                periods[message['Day_period'].value] += 1
                total_messages += 1

            rows.append([*periods.values(), total_messages])

        return DataFrame(rows, index=index, columns=columns)

    @generate_chart(
        bars=SUB_PERIODS,
        lines=['Qty_messages'],
        title='Amount by Month'
    )
    def by_sub_periods(self) -> DataFrame:
        """Shows which sub-periods of the day the chat is most active.
        
        Currently, the sub-periods are:

        - Resting
        - Transport (morning)
        - Work (morning)
        - Lunch
        - Work (evening)
        - Transport (evening)
        - Second Office Hour

        For more information, see :class:`.SubPeriod`.
        """
        chat = self.chats[0]
        data: DefaultDict[str, List[Message]] = defaultdict(list)

        columns = SUB_PERIODS.copy()
        columns.append('Qty_messages')

        rows: List[List[int]] = []

        for message in chat.messages:
            index = message.created_at.replace(
                day=1, hour=0, minute=0, second=0
            )
            data[index.strftime('%B %Y')].append(message)

        index = list(data.keys())

        for messages in data.values():
            sub_periods = {v: 0 for v in SUB_PERIODS}
            total_messages = 0

            for message in messages:
                sub_periods[message['Day_sub_period'].value] += 1
                total_messages += 1

            rows.append([*sub_periods.values(), total_messages])

        return DataFrame(rows, index=index, columns=columns)

    @generate_chart(
        bars=['Qty_char_!', 'Qty_char_?'],
        lines=['Qty_char_text', 'Qty_messages'],
        title='Amount by Month'
    )
    def by_punctuation_marks(self) -> DataFrame:
        """Shows which punctuation marks are used most in the chat
        ordered by month.
        
        Currently, the punctuation marks sought are:

        - ``!``
        - ``?``
        """
        chat = self.chats[0]
        data: DefaultDict[str, List[Message]] = defaultdict(list)

        columns = [
            'Qty_char_!', 'Qty_char_?',
            'Qty_char_text', 'Qty_messages'
        ]
        rows: List[List[int]] = []

        for message in chat.messages:
            index = message.created_at.replace(hour=0, minute=0, second=0)
            data[index.strftime('%B %Y')].append(message)

        index = list(data.keys())

        for messages in data.values():
            exclamation_marks = 0
            question_marks = 0
            text_content = 0
            total_messages = 0

            for message in messages:
                exclamation_marks += get_length(message['Qty_char_!'])
                question_marks += get_length(message['Qty_char_?'])
                text_content += len(message['Qty_char_text'])
                total_messages += 1

            rows.append([
                exclamation_marks, question_marks,
                text_content, total_messages
            ])

        return DataFrame(rows, index=index, columns=columns)


class ActorsFeature(BaseFeature):
    """A feature that adds charts generator related to chat actors.
    
    .. note::

        This feature is already automatically added to Qualichat.

    Attributes
    ----------
    chats: List[:class:`.Chat`]
        All the chats loaded via :meth:`qualichat.load_chats`.
    """

    __slots__ = ()

    @generate_chart(
        bars=[
            'Qty_char_numbers', 'Qty_char_emoji',
            'Qty_char_marks', 'Qty_char_laughs'
        ],
        lines=['Qty_messages'],
        title='Amount by Actor'
    )
    def fabrications(self, *, start: int = 0, end: int = 10) -> NDFrame:
        """Shows what are the most common fabrications aspects in
        messages per actor.

        Fabrication aspects can be interpreted as:

        - Laughs
        - Marks
        - Emojis
        - Numbers
        
        And it will be compared with the total messages sent per actor.
        """
        chat = self.chats[0]

        columns = [
            'Qty_char_numbers', 'Qty_char_emoji',
            'Qty_char_marks', 'Qty_char_laughs',
            'Qty_messages'
        ]

        index = [actor.display_name for actor in chat.actors]
        rows: List[List[int]] = []

        for actor in chat.actors:
            numbers = 0
            emojis = 0
            marks = 0
            laughs = 0

            for message in actor.messages:
                numbers += get_length(message['Qty_char_numbers'])
                laughs += get_length(message['Qty_char_laughs'])
                marks += get_length(message['Qty_char_marks'])
                emojis += get_length(message['Qty_char_emoji'])

            rows.append([numbers, laughs, marks, emojis, len(actor.messages)])

        dataframe = DataFrame(rows, index=index, columns=columns)
        return dataframe.sort_values(by=columns, ascending=False)[start:end]

    @generate_chart(
        bars=['Qty_char_links', 'Qty_char_emails', 'Qty_char_mentions'],
        lines=['Qty_messages'],
        title='Amount by Actor'
    )
    def laminations(self, *, start: int = 0, end: int = 10) -> NDFrame:
        """Shows what are the most common lamination aspects in
        messages per actor.

        Lamination aspects can be interpreted as:

        - Links/URLs
        - E-mails
        - Mentions

        And it will be compared with the total messages sent per actor.
        """
        chat = self.chats[0]

        columns = [
            'Qty_char_links', 'Qty_char_emails',
            'Qty_char_mentions', 'Qty_messages'
        ]

        index = [actor.display_name for actor in chat.actors]
        rows: List[List[int]] = []

        for actor in chat.actors:
            links = 0
            emails = 0
            mentions = 0
            total_messages = 0

            for message in actor.messages:
                links += get_length(message['Qty_char_links'])
                emails += get_length(message['Qty_char_emails'])
                mentions += get_length(message['Qty_char_mentions'])
                total_messages += 1

            rows.append([links, emails, mentions, total_messages])

        dataframe = DataFrame(rows, index=index, columns=columns)
        return dataframe.sort_values(by=columns, ascending=False)[start:end]

    @generate_chart(
        bars=['Qty_char_net', 'Qty_char_text'],
        lines=['Qty_messages'],
        title='Amount by Actor'
    )
    def by_activity(self, *, start: int = 0, end: int = 10) -> NDFrame:
        """Shows which actor send the most characters in the chat."""
        chat = self.chats[0]

        columns = ['Qty_char_net', 'Qty_char_text', 'Qty_messages']

        index = [actor.display_name for actor in chat.actors]
        rows: List[List[int]] = []

        for actor in chat.actors:
            net_content = 0
            text_content = 0

            for message in actor.messages:
                net_content += len(message['Qty_char_net'])
                text_content += len(message['Qty_char_text'])

            rows.append([net_content, text_content, len(actor.messages)])

        dataframe = DataFrame(rows, index=index, columns=columns)
        return dataframe.sort_values(by=columns, ascending=False)[start:end]

    @generate_chart(
        bars=['Qty_char_!', 'Qty_char_?'],
        lines=['Qty_messages'],
        title='Amount by Actor'
    )
    def by_punctuation_marks(
        self, *, start: int = 0, end: int = 10
    ) -> NDFrame:
        """Shows which punctuation marks are used most in the chat
        ordered by actor.
        
        Currently, the punctuation marks sought are:

        - ``!``
        - ``?``
        """
        chat = self.chats[0]

        columns = ['Qty_char_!', 'Qty_char_?', 'Qty_messages']
        index = [actor.display_name for actor in chat.actors]

        rows: List[List[int]] = []

        for actor in chat.actors:
            exclamation_marks = 0
            question_marks = 0
            total_messages = 0

            for message in actor.messages:
                exclamation_marks += get_length(message['Qty_char_!'])
                question_marks += get_length(message['Qty_char_?'])
                total_messages += 1

            rows.append([exclamation_marks, question_marks, total_messages])

        dataframe = DataFrame(rows, index=index, columns=columns)
        return dataframe.sort_values(by=columns, ascending=False)[start:end]

    @generate_chart(
        bars=[
            'Super Fast Interactions', 'Fast Interactions',
            'Regular Interactions', 'Late Interactions'
        ],
        lines=['Qty_messages'],
        title='Amount by Actor'
    )
    def interaction_interval(
        self,
        *,
        start: int = 0,
        end: int = 10
    ) -> NDFrame:
        """Shows the interaction interval between messages per actor.

        There are four levels of interaction range:

        - Super Fast Interactions (<30 seconds)
        - Fast Interactions (30-60 seconds)
        - Regular Interactions (60-120 seconds)
        - Late Interactions (>120 seconds)
        """
        chat = self.chats[0]

        columns = [
            'Super Fast Interactions', 'Fast Interactions',
            'Regular Interactions', 'Late Interactions',
            'Qty_messages'
        ]

        rows: List[List[int]] = []
        index = [actor.display_name for actor in chat.actors]

        for actor in chat.actors:
            super_fast_interactions = 0
            fast_interactions = 0
            regular_interactions = 0
            late_interactions = 0

            for i, message in enumerate(chat.messages[1:]):
                if message.actor != actor:
                    continue

                previous = chat.messages[i]

                delta = message.created_at - previous.created_at
                seconds = delta.total_seconds()

                if seconds <= 30:
                    super_fast_interactions += 1
                elif 30 < seconds <= 60:
                    fast_interactions += 1
                elif 60 < seconds <= 120:
                    regular_interactions += 1
                else:
                    late_interactions += 1

            rows.append([
                super_fast_interactions,
                fast_interactions,
                regular_interactions,
                late_interactions,
                len(actor.messages)
            ])

        dataframe = DataFrame(rows, index=index, columns=columns)
        return dataframe.sort_values(by=columns, ascending=False)[start:end]


class TimeFeature(BaseFeature):
    """A feature that adds charts generator related to chat timing.
    
    .. note::

        This feature is already automatically added to Qualichat.

    Attributes
    ----------
    chats: List[:class:`.Chat`]
        All the chats loaded via :meth:`qualichat.load_chats`.
    """

    __slots__ = ()

    @staticmethod
    def get_interation_timings(messages: List[Message]) -> List[int]:
        super_fast_interactions = 0
        fast_interactions = 0
        regular_interactions = 0
        late_interactions = 0

        for i, message in enumerate(messages[1:]):
            previous = messages[i]

            delta = message.created_at - previous.created_at
            seconds = delta.total_seconds()

            if seconds <= 30:
                super_fast_interactions += 1
            elif 30 < seconds <= 60:
                fast_interactions += 1
            elif 60 < seconds <= 120:
                regular_interactions += 1
            else:
                late_interactions += 1

        return [
            super_fast_interactions,
            fast_interactions,
            regular_interactions,
            late_interactions
        ]

    @generate_chart(
        bars=[
            'Super Fast Interactions', 'Fast Interactions',
            'Regular Interactions', 'Late Interactions'
        ],
        lines=['Qty_messages'],
        title='Amount by Month'
    )
    def interaction_interval(self) -> DataFrame:
        """Shows the interaction interval between messages per month.

        There are four levels of interaction range:

        - Super Fast Interactions (<30 seconds)
        - Fast Interactions (30-60 seconds)
        - Regular Interactions (60-120 seconds)
        - Late Interactions (>120 seconds)
        """
        chat = self.chats[0]
        data: DefaultDict[str, List[Message]] = defaultdict(list)

        columns = [
            'Super Fast Interactions', 'Fast Interactions',
            'Regular Interactions', 'Late Interactions',
            'Qty_messages'
        ]
        rows: List[List[int]] = []

        for message in chat.messages:
            data[message.created_at.strftime('%B %Y')].append(message)

        index = list(data.keys())

        for messages in data.values():
            interactions = self.get_interation_timings(messages)
            rows.append([*interactions, len(messages)])

        return DataFrame(rows, index=index, columns=columns)

    @generate_chart(
        bars=[
            'Super Fast Interactions', 'Fast Interactions',
            'Regular Interactions', 'Late Interactions'
        ],
        lines=['Qty_messages'],
        title='Amount by Weekday'
    )
    def interaction_interval_per_weekday(self) -> DataFrame:
        """Shows the interaction interval between messages per weekday.
        
        There are four levels of interaction range:

        - Super Fast Interactions (<30 seconds)
        - Fast Interactions (30-60 seconds)
        - Regular Interactions (60-120 seconds)
        - Late Interactions (>120 seconds)
        """
        chat = self.chats[0]
        data: Dict[str, List[Message]] = {w: [] for w in WEEKDAYS}

        columns = [
            'Super Fast Interactions', 'Fast Interactions',
            'Regular Interactions', 'Late Interactions',
            'Qty_messages'
        ]
        rows: List[List[int]] = []

        for message in chat.messages:
            data[message.created_at.strftime('%A')].append(message)

        index = list(data.keys())

        for messages in data.values():
            interactions = self.get_interation_timings(messages)
            rows.append([*interactions, len(messages)])

        return DataFrame(rows, index=index, columns=columns)


nlp = spacy.load('pt_core_news_sm') # type: ignore


class NounsFeature(BaseFeature):
    """Textual structure analysis feature, specific for nouns.
    
    .. note::

        This feature is already automatically added to Qualichat.

    Attributes
    ----------
    chats: List[:class:`.Chat`]
        All the chats loaded via :meth:`qualichat.load_chats`.
    """

    __slots__ = ()

    @generate_word_cloud()
    def word_cloud(self) -> WordCloud: # type: ignore
        """Shows a word cloud with the most spoken nouns in the
        chat.
        """
        chat = self.chats[0]
        data: List[str] = []

        for i, message in enumerate(chat.messages, start=1):
            if message['Type'] is not MessageType.default:
                continue

            text = message['Qty_char_text']
            doc = nlp(text) # type: ignore

            for token in doc: # type: ignore
                if token.pos_ == 'NOUN': # type: ignore
                    data.append(token.text) # type: ignore

            progress_bar(i, len(chat.messages))

        all_words = ' '.join(data)
        return WordCloud().generate(all_words) # type: ignore


class VerbsFeature(BaseFeature):
    """Textual structure analysis feature, specific for verbs.
    
    .. note::

        This feature is already automatically added to Qualichat.

    Attributes
    ----------
    chats: List[:class:`.Chat`]
        All the chats loaded via :meth:`qualichat.load_chats`
    """

    __slots__ = ()

    @generate_word_cloud()
    def word_cloud(self) -> WordCloud: # type: ignore
        """Shows a word cloud with the most spoken nouns in the
        chat.
        """
        chat = self.chats[0]
        data: List[str] = []

        for i, message in enumerate(chat.messages, start=1):
            if message['Type'] is not MessageType.default:
                continue

            text = message['Qty_char_text']
            doc = nlp(text) # type: ignore

            for token in doc: # type: ignore
                if token.pos_ == 'VERB': # type: ignore
                    data.append(token.text) # type: ignore

            progress_bar(i, len(chat.messages))

        all_words = ' '.join(data)
        return WordCloud().generate(all_words) # type: ignore


class EmojisFeature(BaseFeature):
    """A feature that adds charts generator related to emojis.
    
    .. note::

        This feature is already automatically added to Qualichat.

    Attributes
    ----------
    chats: List[:class:`.Chat`]
        All the chats loaded via :meth:`qualichat.load_chats`.
    """

    __slots__ = ()

    @generate_chart(bars=['Qty_char_emoji'], title='Amount by Actor')
    def per_user(self, *, start: int = 0, end: int = 10) -> NDFrame:
        """Shows the amount of emoji uploaded per user."""
        chat = self.chats[0]

        columns = ['Qty_char_emoji', 'Qty_messages']
        index = [actor.display_name for actor in chat.actors]

        rows: List[List[int]] = []

        for actor in chat.actors:
            emojis = 0
            messages = 0

            for message in actor.messages:
                emojis += len(message['Qty_char_emoji'])
                messages += 1

            rows.append([emojis, messages])

        dataframe = DataFrame(rows, index=index, columns=columns)
        return dataframe.sort_values(by=columns, ascending=False)[start:end]
