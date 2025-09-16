#!/usr/bin/env python3
"""
Fresh 3000 Domain Discovery - Tạo mới hoàn toàn 3000 domain
Chỉ HTTPS, 200 OK, không redirect, timeout 10s
"""

import requests
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib3
import random
import itertools
import string

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Fresh3000DomainDiscovery:
    def __init__(self):
        self.valid_domains = set()
        self.lock = threading.Lock()
        self.output_file = "fresh-3000-domains.txt"
        self.target_count = 3000
        
        # Comprehensive wordlist
        self.words = [
            # Tech basics
            'admin', 'api', 'app', 'auth', 'auto', 'blog', 'bot', 'box', 'buy', 'cache',
            'call', 'car', 'cat', 'chat', 'check', 'click', 'client', 'cloud', 'code', 'config',
            'copy', 'cpu', 'data', 'db', 'debug', 'demo', 'dev', 'doc', 'down', 'edit',
            'email', 'error', 'event', 'exec', 'exit', 'fast', 'file', 'find', 'fix', 'flag',
            'form', 'free', 'full', 'game', 'get', 'git', 'go', 'good', 'gpu', 'hash',
            'help', 'home', 'host', 'html', 'http', 'hub', 'icon', 'id', 'info', 'init',
            'input', 'item', 'job', 'join', 'json', 'jump', 'key', 'lab', 'last', 'link',
            'list', 'live', 'load', 'lock', 'log', 'login', 'loop', 'mail', 'main', 'make',
            'map', 'max', 'menu', 'meta', 'min', 'mode', 'move', 'name', 'net', 'new',
            'next', 'node', 'null', 'old', 'open', 'opt', 'page', 'pay', 'pic', 'ping',
            'plan', 'play', 'plus', 'port', 'post', 'pro', 'push', 'query', 'quit', 'read',
            'real', 'red', 'ref', 'repo', 'rest', 'run', 'safe', 'save', 'scan', 'search',
            'sell', 'send', 'server', 'set', 'shop', 'show', 'size', 'skip', 'soft', 'sort',
            'src', 'start', 'stop', 'store', 'sub', 'sum', 'sun', 'sync', 'tag', 'task',
            'tax', 'test', 'text', 'time', 'tip', 'tmp', 'top', 'track', 'tree', 'true',
            'try', 'type', 'up', 'url', 'use', 'user', 'view', 'web', 'win', 'work',
            'xml', 'zip', 'zone', 'zero',
            
            # Business words
            'bank', 'card', 'cash', 'cost', 'deal', 'fund', 'loan', 'market', 'money', 'price',
            'profit', 'rent', 'sale', 'spend', 'trade', 'value', 'wealth', 'asset', 'budget',
            'credit', 'debit', 'finance', 'invest', 'lease', 'stock', 'bond', 'equity',
            
            # Short common words  
            'ace', 'add', 'all', 'and', 'any', 'are', 'art', 'ask', 'bad', 'bar', 'bat',
            'bed', 'bee', 'bet', 'bit', 'boy', 'bug', 'bus', 'but', 'bye', 'can', 'cap',
            'cut', 'day', 'dog', 'ear', 'eat', 'egg', 'end', 'eye', 'far', 'few', 'fly',
            'for', 'fun', 'got', 'gun', 'hat', 'her', 'him', 'his', 'hit', 'how', 'ice',
            'its', 'joy', 'kid', 'law', 'let', 'lot', 'low', 'man', 'may', 'not', 'now',
            'odd', 'off', 'oil', 'one', 'our', 'out', 'own', 'pet', 'put', 'ran', 'raw',
            'row', 'sad', 'saw', 'say', 'sea', 'see', 'she', 'shy', 'six', 'sky', 'son',
            'tea', 'ten', 'the', 'too', 'two', 'van', 'war', 'was', 'way', 'who', 'why',
            'yes', 'yet', 'you', 'zoo',
            
            # Extended words
            'about', 'above', 'abuse', 'actor', 'acute', 'admit', 'adopt', 'adult', 'after',
            'again', 'agent', 'agree', 'ahead', 'alarm', 'album', 'alert', 'alien', 'align',
            'alike', 'alive', 'allow', 'alone', 'along', 'alter', 'angel', 'anger', 'angle',
            'angry', 'apart', 'apple', 'apply', 'arena', 'argue', 'arise', 'armed', 'armor',
            'array', 'arrow', 'aside', 'asset', 'avoid', 'awake', 'award', 'aware', 'badly',
            'basic', 'batch', 'beach', 'began', 'begin', 'being', 'below', 'bench', 'bikes',
            'bills', 'birth', 'black', 'blade', 'blame', 'blank', 'blast', 'blind', 'block',
            'blood', 'bloom', 'board', 'boost', 'booth', 'bound', 'boxes', 'brain', 'brand',
            'brave', 'bread', 'break', 'breed', 'brick', 'bride', 'brief', 'bring', 'broad',
            'broke', 'brown', 'brush', 'build', 'built', 'bunch', 'burns', 'burst', 'buses',
            
            # More tech terms
            'access', 'action', 'active', 'actual', 'agency', 'agenda', 'almost', 'always',
            'amazon', 'amount', 'animal', 'annual', 'answer', 'anyone', 'anyway', 'appear',
            'around', 'arrive', 'artist', 'assume', 'attack', 'attend', 'author', 'autumn',
            'avenue', 'backup', 'banner', 'basket', 'battle', 'beauty', 'become', 'before',
            'behalf', 'behave', 'behind', 'belief', 'belong', 'benefit', 'beside', 'better',
            'beyond', 'bridge', 'bright', 'broken', 'budget', 'button', 'camera', 'campus',
            'cancel', 'cannot', 'canvas', 'career', 'castle', 'casual', 'caught', 'center',
            'centre', 'chance', 'change', 'charge', 'choice', 'choose', 'chosen', 'circle',
            'client', 'closer', 'coffee', 'column', 'combat', 'coming', 'common', 'comply',
            'copper', 'corner', 'cotton', 'county', 'couple', 'course', 'covers', 'create',
            'credit', 'crisis', 'custom', 'damage', 'danger', 'dealer', 'debate', 'decade',
            'decide', 'defeat', 'defend', 'define', 'degree', 'demand', 'depend', 'deploy',
            'design', 'desire', 'detail', 'detect', 'device', 'dialog', 'dinner', 'direct',
            'divide', 'doctor', 'domain', 'double', 'dragon', 'drawer', 'driver', 'during',
            'easily', 'eating', 'editor', 'effect', 'effort', 'either', 'eleven', 'emerge',
            'employ', 'enable', 'ending', 'energy', 'engage', 'engine', 'enough', 'ensure',
            'entire', 'escape', 'estate', 'ethics', 'europe', 'events', 'every', 'except',
            'excess', 'expand', 'expect', 'expert', 'export', 'extend', 'extent', 'fabric',
            'facing', 'factor', 'failed', 'fairly', 'fallen', 'family', 'famous', 'father',
            'fellow', 'female', 'figure', 'filter', 'finger', 'finish', 'fiscal', 'flight',
            'flower', 'follow', 'forget', 'format', 'former', 'foster', 'fought', 'fourth',
            'friend', 'frozen', 'future', 'garden', 'gather', 'gender', 'gentle', 'giving',
            'global', 'golden', 'ground', 'growth', 'guilty', 'handle', 'happen', 'hardly',
            'having', 'header', 'health', 'height', 'hidden', 'holder', 'honest', 'horror',
            'hoping', 'humans', 'impact', 'import', 'income', 'indeed', 'indoor', 'inform',
            'injury', 'inside', 'intake', 'invite', 'island', 'itself', 'jacket', 'jungle',
            'junior', 'keeper', 'kidney', 'killed', 'killer', 'kindly', 'knight', 'ladder',
            'ladies', 'larger', 'latest', 'latter', 'launch', 'lawyer', 'leader', 'league',
            'leaves', 'legacy', 'legend', 'length', 'lesson', 'letter', 'levels', 'liable',
            'likely', 'linear', 'listen', 'little', 'living', 'locate', 'locked', 'longer',
            'losing', 'lovely', 'loving', 'lowest', 'luxury', 'mainly', 'making', 'manage',
            'manner', 'marble', 'margin', 'marine', 'marker', 'master', 'matter', 'maximum',
            'meadow', 'median', 'medium', 'member', 'memory', 'mental', 'merely', 'merger',
            'method', 'middle', 'miller', 'mining', 'minute', 'mirror', 'mobile', 'modern',
            'modify', 'moment', 'Monday', 'monkey', 'mother', 'motion', 'moving', 'murder',
            'muscle', 'mutual', 'myself', 'narrow', 'nation', 'native', 'nature', 'nearby',
            'nearly', 'needle', 'nephew', 'nicely', 'nobody', 'normal', 'notice', 'notion',
            'number', 'object', 'obtain', 'occupy', 'occurs', 'option', 'orange', 'orders',
            'origin', 'others', 'outfit', 'output', 'oxford', 'packed', 'palace', 'panels',
            'parade', 'parent', 'partly', 'passed', 'patent', 'patrol', 'paying', 'pencil',
            'people', 'period', 'permit', 'person', 'phrase', 'picked', 'pieces', 'places',
            'planet', 'plates', 'player', 'please', 'plenty', 'poetry', 'police', 'policy',
            'polish', 'poorly', 'popular', 'porter', 'poster', 'potato', 'powder', 'powers',
            'pretty', 'prince', 'prison', 'profit', 'proper', 'proven', 'public', 'purple',
            'pursue', 'puzzle', 'quartz', 'rabbit', 'racing', 'random', 'rarely', 'rather',
            'rating', 'reader', 'really', 'reason', 'recall', 'recent', 'record', 'reduce',
            'reform', 'refuse', 'region', 'relate', 'remain', 'remote', 'remove', 'render',
            'repair', 'repeat', 'reply', 'report', 'rescue', 'resist', 'resort', 'result',
            'return', 'reveal', 'review', 'reward', 'riding', 'rising', 'robust', 'rolled',
            'roster', 'rotate', 'rubber', 'ruling', 'runner', 'safety', 'salary', 'sample',
            'saving', 'scheme', 'school', 'science', 'screen', 'script', 'season', 'second',
            'secret', 'sector', 'secure', 'seeing', 'seeking', 'seller', 'senior', 'serious',
            'server', 'settle', 'shadow', 'shaper', 'shared', 'shield', 'should', 'shower',
            'signal', 'silver', 'simple', 'simply', 'single', 'sister', 'sketch', 'skills',
            'smooth', 'social', 'solely', 'solid', 'solve', 'sorry', 'source', 'soviet',
            'spaces', 'speech', 'spirit', 'spoken', 'spread', 'spring', 'square', 'stable',
            'stands', 'stated', 'status', 'stayed', 'steady', 'stocks', 'stolen', 'stores',
            'storms', 'strain', 'strand', 'stream', 'street', 'stress', 'strike', 'string',
            'strips', 'stroke', 'strong', 'struck', 'studio', 'stupid', 'submit', 'sudden',
            'suffer', 'sugar', 'summer', 'summit', 'sunday', 'supply', 'surely', 'survey',
            'switch', 'symbol', 'system', 'tablet', 'taking', 'talent', 'target', 'taught',
            'temple', 'tenant', 'tennis', 'thanks', 'theory', 'thirty', 'though', 'thread',
            'thrown', 'ticket', 'timber', 'tissue', 'titled', 'toilet', 'tomato', 'tongue',
            'topics', 'toward', 'tracks', 'trader', 'trails', 'trains', 'treaty', 'trends',
            'trials', 'tricks', 'triple', 'trucks', 'trying', 'tunnel', 'turned', 'twelve',
            'twenty', 'typing', 'unable', 'united', 'unless', 'unlike', 'update', 'upload',
            'urgent', 'useful', 'vacant', 'valley', 'vendor', 'vessel', 'victim', 'videos',
            'viewer', 'virgin', 'virtue', 'vision', 'visual', 'volume', 'voters', 'waited',
            'walker', 'wallet', 'wanted', 'warming', 'warned', 'wealth', 'weapon', 'weekly',
            'weight', 'wheels', 'window', 'winner', 'winter', 'wisdom', 'within', 'wizard',
            'wonder', 'wooden', 'worker', 'worthy', 'writer', 'yellow', 'younger'
        ]
        
        # Popular TLDs
        self.tlds = [
            '.com', '.org', '.net', '.edu', '.gov', '.io', '.co', '.me', '.us', '.ca',
            '.uk', '.de', '.fr', '.au', '.jp', '.cn', '.in', '.br', '.mx', '.es',
            '.it', '.nl', '.se', '.no', '.fi', '.dk', '.ch', '.at', '.be', '.pt'
        ]
        
        print(f"📚 Loaded {len(self.words)} words, {len(self.tlds)} TLDs")
        print(f"🎯 Target: {self.target_count} FRESH domains")
    
    def generate_fresh_domains(self, count=100000):
        """Generate fresh domain combinations"""
        domains = set()
        
        # Single word domains
        for word in self.words:
            for tld in self.tlds:
                domains.add(f"{word}{tld}")
        
        # Word + number combinations
        for word in self.words[:200]:  # Use first 200 words
            for num in range(1, 100):  # 1-99
                for tld in self.tlds[:10]:  # Top 10 TLDs
                    domains.add(f"{word}{num}{tld}")
        
        # Two word combinations (shorter words only)
        short_words = [w for w in self.words if len(w) <= 5]
        for w1, w2 in itertools.combinations(short_words[:100], 2):
            for tld in self.tlds[:8]:
                domains.add(f"{w1}{w2}{tld}")
                domains.add(f"{w1}-{w2}{tld}")
        
        # Three letter combinations
        for a, b, c in itertools.product(string.ascii_lowercase, repeat=3):
            combo = f"{a}{b}{c}"
            if combo not in ['www', 'ftp', 'ssh']:  # Skip common prefixes
                for tld in self.tlds[:5]:
                    domains.add(f"{combo}{tld}")
        
        result = list(domains)[:count]
        random.shuffle(result)
        return result
    
    def check_https_only(self, domain):
        """Check HTTPS only, 200 OK, no redirects, 10s timeout"""
        try:
            url = f"https://{domain}"
            response = requests.get(
                url,
                timeout=10,
                allow_redirects=False,  # NO redirects!
                verify=False,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,*/*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Connection': 'close',
                }
            )
            
            if response.status_code == 200:
                content_length = len(response.content) if response.content else 0
                
                # Must have reasonable content
                if content_length >= 200:  # At least 200 bytes
                    return True, f"HTTPS-200-{content_length}b"
                else:
                    return False, f"https-200-small-{content_length}b"
            else:
                return False, f"https-{response.status_code}"
                
        except requests.exceptions.Timeout:
            return False, "https-timeout"
        except requests.exceptions.ConnectionError:
            return False, "https-connection-error"
        except Exception as e:
            return False, f"https-error-{type(e).__name__}"
    
    def save_domain(self, domain, status):
        """Save valid domain immediately"""
        with self.lock:
            if domain not in self.valid_domains:
                self.valid_domains.add(domain)
                
                with open(self.output_file, 'a', encoding='utf-8') as f:
                    f.write(f"{domain}\n")
                
                count = len(self.valid_domains)
                print(f"✅ [{count:4d}] {domain} ({status})")
                return count
        return len(self.valid_domains)
    
    def discover_fresh_3000(self, max_workers=40):
        """Discover 3000 fresh domains"""
        print(f"🚀 Starting FRESH 3000 domain discovery...")
        print(f"📏 Rules: HTTPS ONLY, 200 OK, ≥200 bytes, NO redirects, 10s timeout")
        print(f"🧵 Using {max_workers} threads")
        
        # Clear output file
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(f"# Fresh 3000 domains - {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Generate test domains
        test_domains = self.generate_fresh_domains(100000)
        print(f"🎯 Testing {len(test_domains)} generated domains")
        print("="*80)
        
        start_time = time.time()
        completed = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_domain = {
                executor.submit(self.check_https_only, domain): domain
                for domain in test_domains
            }
            
            for future in as_completed(future_to_domain):
                domain = future_to_domain[future]
                completed += 1
                
                try:
                    is_valid, status = future.result()
                    
                    if is_valid:
                        current_count = self.save_domain(domain, status)
                        
                        if current_count >= self.target_count:
                            print(f"\n🎉 TARGET REACHED! Found {current_count} domains")
                            break
                    
                    # Progress report
                    if completed % 500 == 0:
                        elapsed = time.time() - start_time
                        rate = completed / elapsed if elapsed > 0 else 0
                        valid = len(self.valid_domains)
                        remaining = self.target_count - valid
                        print(f"📊 {completed:5d}/{len(test_domains)} | ✅{valid:4d} valid | 🎯{remaining:4d} needed | {rate:5.1f}/sec")
                        
                except Exception as e:
                    print(f"💥 {domain}: {e}")
        
        final_count = len(self.valid_domains)
        total_time = time.time() - start_time
        
        print(f"\n🏁 FINAL RESULTS:")
        print(f"   ✅ Found: {final_count} valid domains")
        print(f"   ⏱️ Time: {total_time:.1f} seconds")
        print(f"   📊 Rate: {final_count/total_time:.1f} domains/minute")
        print(f"   📁 Output: {self.output_file}")
        
        return final_count

def main():
    discovery = Fresh3000DomainDiscovery()
    
    try:
        count = discovery.discover_fresh_3000(max_workers=40)
        print(f"\n✅ SUCCESS: {count} FRESH domains discovered!")
        
    except KeyboardInterrupt:
        print(f"\n🛑 Stopped. Found {len(discovery.valid_domains)} domains so far.")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()