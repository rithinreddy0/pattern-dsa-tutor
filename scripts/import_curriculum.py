"""Import pinned MIT-licensed learning material. Never executes upstream code."""
from pathlib import Path
from urllib.parse import quote
import hashlib
import json
import re
import subprocess
from collections import Counter
from original_curriculum import originals

ROOT = Path(__file__).resolve().parent.parent
UPSTREAM = ROOT / 'third_party' / 'upstream'
REPO = 'https://github.com/Kartavya728/Data-Structure-and-Algorithms-Sheet'
PIN = '1ef6eec5cb6a103246ce2f54fe0977b6dd9ff2c8'
TAXONOMY = [
    ('Foundations', ['Language basics', 'Patterns', 'Mathematics', 'Complexity']),
    ('Arrays', ['Sorting', 'Fundamentals', 'Subarrays & hashing', 'Matrices']),
    ('Binary Search', ['One-dimensional search', 'Search on answers', 'Two-dimensional search']),
    ('Strings', ['Fundamentals', 'String matching', 'Advanced strings']),
    ('Linked Lists', ['Singly linked lists', 'Doubly linked lists', 'Fast & slow pointers', 'Advanced linked lists']),
    ('Recursion & Backtracking', ['Recursion basics', 'Subsequences', 'Backtracking']),
    ('Bit Manipulation', ['Bit fundamentals', 'Bit problems']),
    ('Stacks & Queues', ['Implementation', 'Expression conversion', 'Monotonic stack', 'Advanced stacks & queues']),
    ('Sliding Window', ['Fixed & variable windows', 'Two pointers']),
    ('Heaps', ['Heap fundamentals', 'Priority queue problems']),
    ('Greedy', ['Greedy basics', 'Scheduling & intervals']),
    ('Binary Trees', ['Traversals', 'Views & paths', 'Tree construction', 'Advanced trees']),
    ('Binary Search Trees', ['BST fundamentals', 'BST problems']),
    ('Graphs', ['Traversal', 'Cycles & topology', 'Shortest paths', 'Spanning trees & DSU', 'Bridges & components']),
    ('Dynamic Programming', ['Introduction & 1D', 'Grids', 'Subsequences', 'Strings', 'Stocks', 'LIS', 'Partition & squares']),
    ('Tries', ['Trie fundamentals', 'Trie & XOR problems']),
]
TOPIC_HINTS = [
    'Work through the smallest valid input by hand. Which operations grow with the input size?',
    'Ask what information from the part of the array you have already visited would help with the next element.',
    'Look for a monotonic condition: once it becomes true, does it stay true for larger candidates?',
    'Consider what you can remember about the prefix you have already scanned.',
    'Draw a three-node list and label the links that must survive before changing any pointer.',
    'Describe the decision at one step, then ask what smaller version of the problem remains.',
    'Write a small example in binary and focus on the bit that distinguishes the cases.',
    'Think about which unresolved elements should remain available when the next element arrives.',
    'Decide what makes a window valid and which boundary should move when it stops being valid.',
    'Which element do you need to access repeatedly: the minimum, maximum, or kth candidate?',
    'What local choice looks promising? Try to prove that exchanging another choice for it cannot hurt.',
    'Describe what information a subtree can return to its parent without revisiting its nodes.',
    'Use the ordering relationship between a node and its two subtrees to discard unnecessary work.',
    'First decide whether edges have weights and whether revisiting a vertex can improve your answer.',
    'Define a state using only the information that changes between two recursive calls.',
    'Think of each prefix as a path. Which information belongs at each node along that path?',
]


def clean_title(name):
    value = re.sub(r'^(?:[a-z]\s*[-.]\s*|\d+\s*[.)-]\s*)', '', name, flags=re.I)
    value = value.replace('_', ' ').strip()
    return {'2Sum Problem': 'Two Sum', '3Sum Problem': '3Sum', '4Sum Problem': '4Sum'}.get(value, value)


def categorize(path):
    parts = path.parts
    first = parts[0]
    mapping = [('1.',0),('2.',1),('3.',1),('4.',2),('5.',3),('6.',4),('7.',5),('8.',6),('9.',7),('a(10)',8),('b(11)',9),('c(12)',10),('d(13)',11),('e.',12),('f.',13),('g.',14),('h.',15),('i.',3)]
    index = next((i for prefix, i in mapping if first.startswith(prefix)), 0)
    topic, subs = TAXONOMY[index]
    text = str(path).lower()
    if first.startswith('2.'):
        sub = 'Sorting'
    elif index == 14:
        dp = [('1.',0),('2.',0),('3.',1),('4.',2),('5.',3),('6.',4),('7.',5),('8.',6),('9.',6)]
        sub = subs[next((i for prefix, i in dp if len(parts)>1 and parts[1].startswith(prefix)), 0)]
    else:
        rules = {
            0:[('pattern',1),('math',2),('complex',3)],
            1:[('matrix',3),('matrices',3),('subarray',2),('sum',2),('hard',2),('medium',2)],
            2:[('answer',1),('2d',2),('2-d',2)],
            3:[('kmp',1),('matching',1),('prefix',1),('hard',2)],
            4:[('doubly',1),('double',1),('cycle',2),('middle',2),('hard',3)],
            5:[('subsequence',1),('combination',1),('hard',2),('backtrack',2),('queen',2)],
            6:[('problem',1)],
            7:[('infix',1),('postfix',1),('prefix',1),('monotonic',2),('nge',2),('hard',3)],
            8:[('pointer',1)], 9:[('problem',1),('hard',1)], 10:[('hard',1),('interval',1),('meeting',1)],
            11:[('path',1),('view',1),('construct',2),('hard',3)], 12:[('problem',1)],
            13:[('topo',1),('cycle',1),('shortest',2),('dijkstra',2),('spanning',3),('disjoint',3),('mst',3),('bridge',4),('kosaraju',4)],
            15:[('problem',1)],
        }
        sub = subs[next((i for word, i in rules.get(index, []) if word in text), 0)]
    return index, topic, sub


def section(comment, key, next_keys):
    pattern = rf'{key}\s*:\s*(.*?)(?=(?:{"|".join(next_keys)})\s*:|\Z)'
    match = re.search(pattern, comment, re.I | re.S)
    return match.group(1).strip() if match else ''


def main():
    if not UPSTREAM.exists():
        subprocess.run(['git','clone','--depth','1', REPO+'.git', str(UPSTREAM)], check=True)
    sha = subprocess.check_output(['git','-C',str(UPSTREAM),'rev-parse','HEAD'], text=True).strip()
    if sha != PIN:
        raise SystemExit(f'Expected pinned source {PIN}, got {sha}; review upstream before changing the pin.')
    license_text = (UPSTREAM / 'LICENSE').read_text(encoding='utf-8')
    if 'MIT License' not in license_text or 'Kartavya' not in license_text:
        raise SystemExit('Source license check failed')
    problems = []
    for file in sorted(UPSTREAM.rglob('*.cpp')):
        raw = file.read_text(encoding='utf-8', errors='replace').strip()
        if len(raw) < 60:
            continue
        relative = file.relative_to(UPSTREAM)
        index, topic, subtopic = categorize(relative)
        title = clean_title(file.stem)
        blocks = '\n'.join(re.findall(r'/\*(.*?)\*/', raw, re.S))
        statement = section(blocks, 'Question', ['Explanation','Approach','Time Complexity','Space Complexity'])
        explanation = section(blocks, 'Explanation', ['Time Complexity','Space Complexity','Question']) or section(blocks, 'Approach', ['Time Complexity','Space Complexity','Question'])
        time_match = re.search(r'Time Complexity\s*:\s*([^\n]+)', blocks, re.I)
        space_match = re.search(r'Space Complexity\s*:\s*([^\n]+)', blocks, re.I)
        solution = re.sub(r'/\*.*?\*/', '', raw, flags=re.S).strip()
        source_url = f'{REPO}/blob/{sha}/{quote(relative.as_posix(), safe="/")}'
        # Preserve missing source context honestly; no invented statement or complexity.
        if not statement:
            statement = f'Practice task: {title}. Study the linked community implementation, identify its input and output contract, and implement the same operation. The upstream file does not provide a separate full problem statement.'
        if not explanation:
            explanation = f'The community source provides an implementation of {title} without a separate editorial. Read the implementation in Solution mode, trace a small example, and identify the invariant before deriving its complexity.'
        difficulty = 'Hard' if 'hard' in str(relative).lower() else 'Easy' if 'easy' in str(relative).lower() or index == 0 else 'Medium'
        slug = re.sub(r'[^a-z0-9]+','-', title.lower()).strip('-')[:65] + '-' + hashlib.sha256(relative.as_posix().encode()).hexdigest()[:8]
        problems.append({'id':slug, 'title':title, 'topic':topic, 'subtopic':subtopic, 'difficulty':difficulty, 'statement':statement, 'hints':[TOPIC_HINTS[index]], 'explanation':explanation, 'solution':solution, 'language':'cpp', 'time_complexity':time_match.group(1).strip(' -')[:120] if time_match else 'Not specified in upstream source', 'space_complexity':space_match.group(1).strip(' -')[:120] if space_match else 'Not specified in upstream source', 'source_url':source_url, 'source_name':'Kartavya728 · Striver A2Z community solutions', 'license':'MIT', 'tags':[subtopic, 'Community source']})
    # An independently written, fully explained reference for the first learning session.
    for p in problems:
        if p['title'] == 'Two Sum' and p['topic'] == 'Arrays':
            p.update(statement='Given an integer array nums and a target, return the indices of two distinct elements whose sum equals the target. Assume exactly one pair exists. Example: nums = [2, 7, 11, 15], target = 9 → [0, 1]. The same element cannot be used twice.', hints=['For the current value x, which value would complete the target? Think about how to find that value among elements you have already visited.'], explanation='A direct approach checks every pair in O(n²) time. To avoid repeated searches, keep a hash map from previously seen values to their indices. Before inserting nums[i], look up target − nums[i]. If it exists, those two indices form the answer. Looking up before insertion prevents reusing the current element. The invariant is that the map contains only indices smaller than i. Every valid pair is found when its later index is visited. Expected time is O(n); extra space is O(n).', time_complexity='O(n) expected', space_complexity='O(n)')
    imported_count = len(problems)
    original_problems = originals()
    problems.extend(original_problems)
    out = ROOT / 'backend' / 'data'
    out.mkdir(exist_ok=True)
    (out/'problems.json').write_text(json.dumps(problems, ensure_ascii=False, indent=2), encoding='utf-8')
    (out/'originals.json').write_text(json.dumps(original_problems, ensure_ascii=False, indent=2), encoding='utf-8')
    (out/'taxonomy.json').write_text(json.dumps([{'name':name,'subtopics':subs} for name,subs in TAXONOMY], indent=2), encoding='utf-8')
    (ROOT/'third_party'/'KARTAVYA_LICENSE.txt').write_text(license_text, encoding='utf-8')
    sources = {'repository':REPO,'commit':sha,'license':'MIT','copyright':'Copyright (c) 2025 Kartavya Mahesh Suryawanshi','license_text':license_text,'imported_problems':imported_count,'original_problems':len(original_problems),'total_problems':len(problems),'topics':len(TAXONOMY),'subtopics':sum(len(s) for _,s in TAXONOMY),'notes':f'{imported_count} community solutions aligned with Striver A2Z, plus {len(original_problems)} original teaching references for heaps and greedy algorithms. Not affiliated with takeUforward. This snapshot is not a complete copy of the 455-question sheet. Difficulty labels are inferred from source folders, not official ratings. Community implementations are not independently verified. Missing statements, editorials, and complexity are explicitly identified. Hint prompts, taxonomy, and the Two Sum teaching note are original additions.'}
    (out/'sources.json').write_text(json.dumps(sources, indent=2), encoding='utf-8')
    print(json.dumps({'imported':len(problems),'topics':dict(Counter(p['topic'] for p in problems)),'subtopics':sources['subtopics']}))


if __name__ == '__main__':
    main()
