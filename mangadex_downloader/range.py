import re

from .errors import MangaDexException

class InvalidExpression(MangaDexException):
    pass

def _err_invalid_expr(text, err_expr, char, msg):
    copy_text = str(text)
    # Append remaining expression
    expr = ""
    for c in copy_text:
        if c == " ":
            continue
        elif c == ",":
            break
        expr += c
    err_msg = f"Invalid expression \"{err_expr + expr}\", "
    err_msg += msg
    raise InvalidExpression(err_msg)

def _parse_expr(text):
    open_square_bracket = False
    close_square_bracket = False
    found_number = False
    found_not_expr = False
    expr = ""
    list_expr = []

    def reset_state():
        nonlocal open_square_bracket
        nonlocal close_square_bracket
        nonlocal found_number
        nonlocal found_not_expr
        nonlocal expr

        open_square_bracket = False
        close_square_bracket = False
        found_number = False
        found_not_expr = False
        expr = ""

    while True:
        if not text:
            # Add some extra checking for not expression
            if expr == "!" and found_not_expr:
                # ! expr is not followed by the numbers
                # it should be !90, not ! only
                _err_invalid_expr(
                    text,
                    expr,
                    char,
                    'Not (!) expression should be followed by numbers'
                )
            if expr:
                # Append final expression
                list_expr.append(expr)
                reset_state()
            break

        for char in text:
            # Comma or whitespace detected, continue to find other expressions
            if (char == ',' or char == " ") and not found_number and not found_not_expr:
                text = text[len(char):]
                continue
            # We're looking for not expression (!)
            elif char == '!' and not found_not_expr and not found_number:
                expr += char
                found_not_expr = True
                text = text[len(char):]
                continue
            elif found_not_expr:
                # Whitespace detected, we're just gonna ignore it
                if char == " ":
                    text = text[len(char):]
                    continue
                
                if not found_number and char == ',':
                    _err_invalid_expr(
                        text,
                        expr,
                        char,
                        'Not (!) expression should be followed by numbers'
                    )

                if not found_number:
                    num_match = re.search(r'[0-9]{1,}', char)
                    if num_match is not None:
                        next_char = text[len(char):]
                        if not next_char:
                            # There are no more characters in expression
                            expr += num_match.group()
                            list_expr.append(expr)
                            text = next_char
                            reset_state()
                            continue

                        # We have found the numbers
                        expr += num_match.group()
                        found_number = True
                        text = text[len(num_match.group()):]
                        continue
                else:
                    if char == ",":
                        list_expr.append(expr)
                        text = text[len(char):]
                        reset_state()
                        continue

            # We're looking for numbers
            elif not found_number:
                num_match = re.search(r'[0-9-]{1,}', char)
                if num_match is not None:
                    next_char = text[len(char):]
                    if not next_char:
                        # There are no more characters in expression
                        expr += num_match.group()
                        list_expr.append(expr)
                        text = next_char
                        reset_state()
                        continue

                    # We have found the numbers
                    expr += num_match.group()
                    found_number = True
                    text = text[len(num_match.group()):]
                    continue
                else:
                    _err_invalid_expr(text, expr, char, f"Invalid character found = '{char}'")
            elif found_number:
                # Once we found the number we're looking for square brackets [] (pages expression)

                # If close square bracket in front, throw error
                if char == ']' and not open_square_bracket:
                    _err_invalid_expr(text, expr, char, "closing square bracket shouldn\'t be in front")
                
                # We found the opening square bracket
                if char == '[':
                    # Duplicate opening square bracket
                    if open_square_bracket:
                        _err_invalid_expr(text, expr, char, 'Found duplicate opening square bracket')

                    open_square_bracket = True
                    expr += char
                    text = text[len(char):]
                    continue
                
                if open_square_bracket and not close_square_bracket:
                    if char == ']':
                        # Duplicate closing square bracket
                        if close_square_bracket:
                            _err_invalid_expr(text, expr, char, 'Found duplicate closing square bracket')

                        next_char = text[len(char):]
                        if not next_char:
                            # There are no more characters in expression
                            expr += char
                            list_expr.append(expr)
                            text = next_char
                            reset_state()
                            continue

                        close_square_bracket = True
                        expr += char
                        text = text[len(char):]
                        continue
                    # Whitespace detected, we're just gonna ignore it
                    elif char == " ":
                        text = text[len(char):]
                        continue
                    else:
                        # Append additional characters
                        expr += char
                        text = text[len(char):]
                        continue

                # This one has pages specified    
                if open_square_bracket and close_square_bracket:
                    # Comma detected, reset all states and find new expression
                    if char == ',':
                        list_expr.append(expr)
                        text = text[len(char):]
                        reset_state()
                        continue
                    # Whitespace detected, we just ignore it
                    elif char == " ":
                        continue
                    else:
                        _err_invalid_expr(
                            text,
                            expr,
                            char,
                            f'Invalid character found in the end of square bracket = "{char}"'
                        )

                elif char == ',' and not open_square_bracket and not close_square_bracket:
                    list_expr.append(expr)
                    text = text[len(char):]
                    reset_state()
                    continue
                elif open_square_bracket and not close_square_bracket:
                    # We're just ignore it until found closing square bracket
                    continue
                else:
                    # Whitespace detected, we just ignore it
                    if char == " ":
                        text = text[len(char):]
                        continue
                    
                    # In the end of numbers, there are not expression (!)
                    # And it should be marked as illegal
                    if char == "!":
                        _err_invalid_expr(
                            text,
                            expr,
                            char,
                            'Not (!) expression should be not placed in the end of numbers'
                        )

                    expr += char
                    text = text[len(char):]
                    continue

    return list_expr

class _Base:
    def __init__(self):
        self.ignored_nums = []

    def ignore_num(self, expr_num):
        _, num = expr_num.split('!')

        self.ignored_nums.append(float(num))

    def check(self, num):
        return num in self.ignored_nums

class _RangeStartFrom(_Base):
    def __init__(self, expr):
        super().__init__()
        
        start, end = expr.split('-')
        self.start = float(start)

    def check(self, num):
        ignored = super().check()
        if ignored:
            return False

        return num >= self.start

class _RangeEndFrom(_Base):
    def __init__(self, expr):
        super().__init__()

        start, end = expr.split('-')
        self.end = float(end)
    
    def check(self, num):
        ignored = super().check()
        if ignored:
            return False

        return num <= self.end

class _RangeStarttoEnd(_Base):
    def __init__(self, expr):
        super().__init__()

        start, end = expr.split('-')
        self.start = float(start)
        self.end = float(end)
    
    def check(self, num):
        ignored = super().check()
        if ignored:
            return False

        if not (num >= self.start):
            return False
        
        if not (num <= self.end):
            return False
        
        return True


class RangeChecker:
    def __init__(self, expr):
        self.expr = _parse_expr(expr)
        self.checkers = {}
        self._parse()

    def _get_chapter_pages(self, expr):
        # Chapter with pages
        re_chapter_with_pages = r'(?P<chapter>[0-9-]{0,}-[0-9-]{0,}|[0-9]{1,})\[(?P<pages>.{0,})\]'
        match = re.search(re_chapter_with_pages, expr)
        if match is not None:
            return match.group('chapter'), match.group('pages')
        
        # Chapter only
        re_chapter = r'(?P<chapter>[0-9-]{0,}-[0-9-]{0,}|[0-9]{1,})'
        match = re.search(re_chapter, expr)
        if match is not None:
            return match.group('chapter'), None
    
    def _register_chapter_chkr(self, chapter, pages=None):

        pass

    def _parse(self):
        for expr in self.expr:
            chapter, pages = self._get_chapter_pages(expr)