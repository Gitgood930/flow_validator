__author__ = 'David M. Nicol'

import sys
import bisect
from netaddr import *

class MatchFieldElement(object):

    def __init__(self, low, high, tag):
        self._low = low
        self._high = high
        self._tag = tag
        self._size = high - low

class MatchField2(object):

    def __init__(self, field_name):

        self.field_name = field_name
        self._lowDict = {}
        self.ordered = False
        self.ordered = False

    def add_element(self, low, high, tag):

        if not low in self._lowDict:
            self._lowDict[low] = {} 
        
        size = high - low
        if not size in self._lowDict[low]:
            e = MatchFieldElement(low, high, tag)
            self._lowDict[low][size] = e


    def order_elements(self):

        self.ordered = True
        for low in self._lowDict:

            # before: self._lowDict[low] would be a dictionary keyed by sizes containing MatchFieldElement objects
            # after: it will be a list of MatchFieldElement objects ordered by their size

            size_list = sorted(self._lowDict[low].keys())
            elements = []
            for i in xrange(0, len(size_list)):
                elements.append(self._lowDict[low][size_list[i]])

            self._lowDict[low] = elements

    # build data structure suitable for determining intersection of elements
    # This essentially takes form of a dictionary self.pos_dict, keyed by places of 'interest' (pos),
    # i.e._ where elements begin and end, all of these keys are also maintained in a list self.pos_list
    # The dictionary self.pos_dict contains as values a list of three sets;

    # set of all tags of elements that 'occupy'/run through at that place of interest
    # set of all tags of elements that begin at that place of interest
    # set of all tags of elements that end at that place of interest

    def buildQueryMap(self):

        if not self.ordered:
            self.order_elements()

        self.pos_dict = {}
        self.pos_list = []

        for low in self._lowDict:
            if not low in self.pos_dict:

                # record set of ranges that include low, that start at low, and that end at low
                self.pos_dict[low] = [set(), set(), set()]

            # Pick up all elements associated with this low (all various sizes, i.e._)
            elements = self._lowDict[low]
            for j in xrange(0, len(elements)):

                # mark that range begins at low
                self.pos_dict[low][1].add(elements[j].tag)
                high = low + elements[j].size

                if not high in self.pos_dict:
                    self.pos_dict[high] = [set(), set(), set()]

                # mark that range ends at high
                self.pos_dict[high][2].add(elements[j].tag)

        active_tags = set()
        previously_ended_tags = set()

        self.pos_list = sorted(self.pos_dict.keys())
        for pos in self.pos_list:

            [on, start, end] = self.pos_dict[pos]

            # compute the set of elements that include element 'pos'
            active_tags = (active_tags | start) - previously_ended_tags
            self.pos_dict[pos][0] = active_tags
            previously_ended_tags = end

    # Returns a set of tags that intersect between the in_match_field and self
    def intersect(self, in_match_field_element):

        intersecting_set = set()

        intersecting_set = self.cover(in_match_field_element._low,
                                        in_match_field_element._high)

        return intersecting_set

    def complement(self, in_match_field_element):


        complement = self.complement_cover(in_match_field_element._low,
                                           in_match_field_element._high)


    def complement_cover(self, low, high):
        complement = set()

        complement = self.cover(0, sys.maxsize) - self.cover(low, high)
        return complement

    # return a set of element tags that cover the range from low to high
    def cover(self, low, high):

        if 'pos_list' not in self.__dict__:
            self.buildQueryMap()

        # Where do we start the scan?
        # i will be the index for going through pos_list array of places of interest
        i = bisect.bisect_left(self.pos_list, low)

        # If the i falls to the right of all of the places of interest, then you are done, nothing intersects
        if i == len(self.pos_list):
            return set()

        # If i falls to the left of all of the places of interest and...
        # The low and high are such that that will include the first pos_list, then, collect the first one._..
        # This also means that low here is strictly less than self.pos_list[0]

        if i == 0 and low < self.pos_list[0] and self.pos_list[0] <= high:
            pos = self.pos_list[i]
            active_tags = self.pos_dict[pos][0]

        # Sort of special case when i > 0 and there is one more guy which is exactly equal to low but is next to i
        # This seems like it happens because of bisect_left
        # Collect things from this next guy

        elif i > 0 and len(self.pos_list) > 1 and i + 1 < len(self.pos_list) and self.pos_list[i + 1] == low:
            i += 1
            pos = self.pos_list[i]
            active_tags = self.pos_dict[pos][0]

        # value at i is strictly larger than low and value at i-1 is strictly lower, so grab things from i-1
        elif i > 0:
            pos = self.pos_list[i - 1]
            active_tags = self.pos_dict[pos][0] - self.pos_dict[pos][2]
            i -= 1

        # self.pos_list[i] < low or possibly self.pos_list[i] == low
        else:
            if self.pos_list[i] == low:
                pos = self.pos_list[i]
                active_tags = self.pos_dict[pos][1]
            else:
                active_tags = set()


        # Collect elements by sweeping right until you hit _high_
        i += 1
        while i < len(self.pos_list) and self.pos_list[i] <= high:
            pos = self.pos_list[i]
            active_tags = active_tags | self.pos_dict[pos][0]
            i += 1

        return active_tags


class MatchField(object):

    def __init__(self, field_name):

        self.field_name = field_name
        self.pos_list = []
        self.pos_dict = {}
        self.element_dict = {}

    def remove_element_from_pos_dict(self, e):

        # If there is one element left and this is that one last element...
        if len(self.element_dict) == 1 and e._tag in self.element_dict:
            del self.pos_dict[e._low]
            del self.pos_dict[e._high]
            self.pos_list.remove(e._low)
            self.pos_list.remove(e._high)
            return

        # Check what previous ranges, this new range intersects with and update
        for prev_tag in self.cover(e._low, e._high):

            prev = self[prev_tag]

            # If I arrived on to myself, don't do anything...
            if prev._tag == e._tag:
                continue

            if e._low <= prev._low <= e._high and e._tag in self.pos_dict[e._low][0]:
                self.pos_dict[prev._low][0].remove(e._tag)

            if e._low <= prev._high <= e._high and e._tag in self.pos_dict[e._high][0]:
                self.pos_dict[prev._high][0].remove(e._tag)

        # Start with the low index
        if e._tag in self.pos_dict[e._low][0]:
            self.pos_dict[e._low][0].remove(e._tag)

        self.pos_dict[e._low][1].remove(e._tag)

        # Then the high index
        if e._tag in self.pos_dict[e._high][0]:
            self.pos_dict[e._high][0].remove(e._tag)

        self.pos_dict[e._high][2].remove(e._tag)

        # Check if nothing starts/stops at endpoints any more
        # if so, get rid of them from pos_dict and pos_list
        if not len(self.pos_dict[e._low][1]) and not len(self.pos_dict[e._low][2]):
            del self.pos_dict[e._low]
            self.pos_list.remove(e._low)

        if not len(self.pos_dict[e._high][1]) and not len(self.pos_dict[e._high][2]):
            del self.pos_dict[e._high]
            self.pos_list.remove(e._high)

    def add_element_to_pos_dict(self, e):

        def init_pos(pos):
            # If this new endpoint is new add it to appropriate place in pos_list and pos_dict
            if pos not in self.pos_dict:
                self.pos_dict[pos] = [set(), set(), set()]
                bisect.insort(self.pos_list, pos)

        init_pos(e._low)
        self.pos_dict[e._low][0].add(e._tag)
        self.pos_dict[e._low][1].add(e._tag)

        init_pos(e._high)
        self.pos_dict[e._high][0].add(e._tag)
        self.pos_dict[e._high][2].add(e._tag)

        # Check what previous ranges, this new range intersects with and update
        for prev_tag in self.cover(e._low, e._high):
            prev = self[prev_tag]

            # If I arrived on to myself
            if prev._tag == e._tag:
                continue

            if prev._low <= e._low <= prev._high:
                self.pos_dict[e._low][0].add(prev._tag)

            if prev._low <= e._high <= prev._high:
                self.pos_dict[e._high][0].add(prev._tag)

            if e._low <= prev._low <= e._high:
                self.pos_dict[prev._low][0].add(e._tag)

            if e._low <= prev._high <= e._high:
                self.pos_dict[prev._high][0].add(e._tag)

    def __delitem__(self, key):

        self.remove_element_from_pos_dict(self.element_dict[key])
        del self.element_dict[key]

    def keys(self):
        return self.element_dict.keys()

    def values(self):
        return self.element_dict.values()

    def __getitem__(self, item):
        return self.element_dict[item]

    def __setitem__(self, key, e):

        if e._tag != key:
            raise Exception("Invalid element being added tag != key")

        if key in self.element_dict:
            del self[key]
            self.element_dict[key] = e
            self.add_element_to_pos_dict(e)

        else:
            self.element_dict[key] = e
            self.add_element_to_pos_dict(e)


    def complement_cover(self, low, high):
        complement = set()

        #TODO: cover(0, sys.maxsize) should really be something that simple and a constant
        # not required to be computed

        complement = self.cover(0, sys.maxsize) - self.cover(low, high)
        return complement

    # return a set of element tags that cover the range from low to high
    def cover(self, low, high):

        # If there are no elements to intersect this with...
        if not self.element_dict:
            return set()

        if 'pos_list' not in self.__dict__:
            self.buildQueryMap()

        # Where do we start the scan?
        # i will be the index for going through pos_list array of places of interest
        i = bisect.bisect_left(self.pos_list, low)

        # If the i falls to the right of all of the places of interest, then you are done, nothing intersects
        if i == len(self.pos_list):
            return set()

        # Case when the incoming range falls completely to the left of even the first one of pre-existing:
        # Collect the set of the first one
        if i == 0 and low < self.pos_list[0] and self.pos_list[0] <= high:
            pos = self.pos_list[i]
            active_tags = self.pos_dict[pos][0]

        # This seems like it happens because of bisect_left
        # Case when incoming range's low falls right on the pos immediately to the right of i:
        # Collect things from this pos on the right
        elif len(self.pos_list) > 1 and i + 1 < len(self.pos_list) and self.pos_list[i + 1] == low:
            i += 1
            pos = self.pos_list[i]
            active_tags = self.pos_dict[pos][0]


        # i falls in the middle of some things s.t. value at i is strictly larger than low
        # Collect things that are being carried forward from i-i
        elif i > 0:
            pos = self.pos_list[i - 1]
            active_tags = self.pos_dict[pos][0] - self.pos_dict[pos][2]
            i -= 1

        # i == 0 and (low > self.pos_list[0] or self.pos_list[0] == low):
        # Can this even happen?
        else:
            if low > self.pos_list[0]:
                raise Exception("This happened!")

            if self.pos_list[i] == low:
                pos = self.pos_list[i]
                active_tags = self.pos_dict[pos][1]
            else:
                active_tags = set()


        # Collect elements by sweeping right until you hit _high_
        i += 1
        while i < len(self.pos_list) and self.pos_list[i] <= high:
            pos = self.pos_list[i]
            active_tags = active_tags | self.pos_dict[pos][0]
            i += 1

        return active_tags

    # Returns a set of tags that intersect between the in_match_field and self
    def intersect(self, in_match_field_element):

        intersecting_set = set()

        intersecting_set = self.cover(in_match_field_element._low,
                                        in_match_field_element._high)

        return intersecting_set

    def complement(self, in_match_field_element):


        complement = self.complement_cover(in_match_field_element._low,
                                           in_match_field_element._high)



def main():

    m = MatchField("dummy")
    
    m.add_element(1, 3, "tag1")
    m.add_element(1, 4, "tag2")
    m.add_element(7, 9, "tag3")

    print m.cover(2, 10)
    print m.complement_cover(1, 2)


if __name__ == "__main__":
    main()
