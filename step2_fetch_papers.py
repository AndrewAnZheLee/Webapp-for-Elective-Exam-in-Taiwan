import json
import random
import time
import arxiv
import os
import re  # <--- 新增正則表達式套件
from Bio import Entrez

# === 設定區 ===
Entrez.email = "anzhe0327@gmail.com"  # 請務必填寫 email，這是 NCBI 的規定

# 1. 載入課綱
def load_syllabus():
    try:
        with open("syllabus_mapping.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ 找不到 syllabus_mapping.json")
        return None

# 2. 物理抓取器 (arXiv)
def fetch_arxiv(chapter, keyword):
    print(f"⚛️  正在從 arXiv 搜尋物理論文: {keyword}...")
    client = arxiv.Client()
    search = arxiv.Search(
        query=f'abs:"{keyword}" OR ti:"{keyword}"',
        max_results=3,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    
    results = []
    try:
        for result in client.results(search):
            results.append({
                "title": result.title,
                "summary": result.summary.replace("\n", " "),
                "published": result.published.strftime("%Y-%m-%d"),
                "url": result.entry_id,
                "source": "arXiv",
                "mapping_chapter": chapter,
                "mapping_keyword": keyword,
                "subject": "physics"  # ⭐️ 關鍵：明確標記科目
            })
    except Exception as e:
        print(f"arXiv 連線錯誤: {e}")
    
    return results

# 3. 生物/化學抓取器 (PubMed)
def fetch_pubmed(subject, chapter, keyword):
    print(f"🧬 正在從 PubMed 搜尋 {subject} 論文: {keyword}...")
    
    try:
        # 搜尋 ID
        handle = Entrez.esearch(db="pubmed", term=f"{keyword} AND review[Filter]", retmax=3, sort="date")
        record = Entrez.read(handle)
        handle.close()
        
        id_list = record["IdList"]
        if not id_list: return []

        # 抓取內容
        handle = Entrez.efetch(db="pubmed", id=id_list, rettype="xml", retmode="text")
        papers = Entrez.read(handle)
        handle.close()
        
        results = []
        for article in papers['PubmedArticle']:
            try:
                art = article['MedlineCitation']['Article']
                title = art['ArticleTitle']
                
                # 處理摘要
                abstract_list = art.get('Abstract', {}).get('AbstractText', [])
                summary = " ".join([str(x) for x in abstract_list])
                if not summary: continue

                # 處理日期
                pub_date = art['Journal']['JournalIssue']['PubDate']
                year = pub_date.get('Year', '2024') # 預設值防止錯誤
                
                pmid = article['MedlineCitation']['PMID']

                results.append({
                    "title": title,
                    "summary": summary,
                    "published": year,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "source": "PubMed",
                    "mapping_chapter": chapter,
                    "mapping_keyword": keyword,
                    "subject": subject  # ⭐️ 關鍵：明確標記科目
                })
            except:
                continue
        return results

    except Exception as e:
        print(f"PubMed 連線錯誤: {e}")
        return []

def clean_filename(title):
    # 將非法字元替換為底線，並移除多餘空白
    cleaned = re.sub(r'[\\/*?:"<>|]', "_", title)
    return cleaned.strip()

# === 主控制流程 ===
if __name__ == "__main__":
    syllabus = load_syllabus()
    
    if syllabus:
        # A. 隨機決定科目與關鍵字
        subjects = ["physics", "chemistry", "biology"]
        target_subject = random.choice(subjects)
        chapters = list(syllabus[target_subject].keys())
        random_chapter = random.choice(chapters)
        keywords = syllabus[target_subject][random_chapter]
        random_keyword = random.choice(keywords)

        print(f"🎯 目標：{target_subject} | {random_keyword}")

        # B. 抓取
        papers = []
        if target_subject == "physics":
            papers = fetch_arxiv(random_chapter, random_keyword)
        else:
            papers = fetch_pubmed(target_subject, random_chapter, random_keyword)
            
        # C. 存檔 (⚠️ 重大修改)
        if papers:
            target_paper = papers[0]
            
            # 1. 建立分類資料夾：例如 raw_queue/physics
            queue_dir = f"raw_queue/{target_paper['subject']}"
            os.makedirs(queue_dir, exist_ok=True)
            
            # 2. 使用標題作為檔名
            safe_title = clean_filename(target_paper['title'])
            
            # 檔名過長可能會報錯，截取前 100 字元比較保險
            filename = f"{queue_dir}/{safe_title[:100]}.json"
            
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(target_paper, f, indent=4, ensure_ascii=False)
                
            print(f"✅ 抓取成功！")
            print(f"📂 路徑：{filename}")
        else:
            print("❌ 找不到相關論文。")