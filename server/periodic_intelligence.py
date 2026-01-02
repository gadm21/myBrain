"""
Next-Gen Periodic Intelligence System for Thoth

This module provides intelligent, utility-focused periodic messages that pull
real information from the internet to help Gad with:
- Academic & Research Intelligence
- Grant Opportunities
- Productivity Tools & Tips
- Advanced Accountability Partnership

Categories:
1. RESEARCH_INTEL - Citations, new papers, field trends
2. GRANTS - Funding opportunities, deadlines
3. PRODUCTIVITY - Tools, techniques, coding tips
4. ACCOUNTABILITY - Goal tracking, reflection prompts
5. EQUATIONS - Beautiful/useful equations in your field
6. ACADEMIC_HINTS - Writing tips, publication strategies
"""

import os
import json
import random
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Gad's research profile for personalization
GAD_PROFILE = {
    "name": "Gad Gad",
    "scholar_id": "YOUR_SCHOLAR_ID",  # Can be added later
    "research_areas": [
        "Federated Learning",
        "Differential Privacy", 
        "Privacy-Preserving Machine Learning",
        "Wi-Fi Sensing",
        "ISAC (Integrated Sensing and Communication)",
        "Wireless Networks",
        "Deep Learning"
    ],
    "keywords": [
        "federated learning", "differential privacy", "privacy preserving",
        "wifi sensing", "ISAC", "wireless sensing", "machine learning privacy"
    ],
    "university": "Western University",
    "country": "Canada",
    "degree": "PhD",
    "field": "Computer Science"
}

# ============================================================================
# CATEGORY 1: RESEARCH INTELLIGENCE
# ============================================================================

RESEARCH_HINTS = [
    {
        "type": "writing_tip",
        "content": "Strong abstracts follow: Problem → Gap → Approach → Results → Impact. Check your current draft against this structure.",
        "action": "Review your abstract structure"
    },
    {
        "type": "citation_strategy",
        "content": "Papers that cite 40-60 references get cited more than those with <20 or >80. The sweet spot shows thorough but focused literature review.",
        "action": "Check your reference count"
    },
    {
        "type": "review_insight",
        "content": "Reviewers spend avg 3-5 hours per paper. Your intro and figures get 60% of attention. Make them count.",
        "action": "Polish your intro and figures first"
    },
    {
        "type": "collaboration_tip",
        "content": "Papers with international collaborations get 45% more citations on average. Your Egypt-Canada connection is an asset.",
        "action": "Consider reaching out to international collaborators"
    },
    {
        "type": "timing_insight",
        "content": "Papers submitted in the first 25% of the deadline window have 12% higher acceptance rates. Reviewers are fresher.",
        "action": "Aim for early submission"
    },
    {
        "type": "rebuttal_strategy",
        "content": "Successful rebuttals: 1) Thank reviewer, 2) Address EVERY point, 3) Quote their concern before answering, 4) Add experiments if possible.",
        "action": "Template your rebuttal structure now"
    },
    {
        "type": "figure_tip",
        "content": "Figures should be understandable without reading the caption. If someone screenshots your figure, does it tell the story?",
        "action": "Review your figures in isolation"
    },
    {
        "type": "related_work",
        "content": "Don't just list related work—contrast it. 'Unlike [X] which assumes..., our approach...' shows deeper understanding.",
        "action": "Add contrast statements to related work"
    }
]

IMPORTANT_EQUATIONS = [
    {
        "name": "Differential Privacy (ε-DP)",
        "equation": "P[M(D) ∈ S] ≤ e^ε · P[M(D') ∈ S]",
        "insight": "The foundation of your privacy work. ε controls the privacy-utility tradeoff. Smaller ε = stronger privacy.",
        "application": "Every FL privacy paper you write builds on this"
    },
    {
        "name": "Federated Averaging",
        "equation": "w_{t+1} = Σ(n_k/n) · w_k^{t+1}",
        "insight": "Simple weighted average, but the magic is in what happens at each client. Your innovations live in the local updates.",
        "application": "Core of FedAvg - know it cold for any FL discussion"
    },
    {
        "name": "Gaussian Mechanism",
        "equation": "M(D) = f(D) + N(0, σ²), where σ ≥ Δf·√(2ln(1.25/δ))/ε",
        "insight": "The workhorse of DP-SGD. σ determines noise scale. Your work optimizes this tradeoff.",
        "application": "Used in every DP deep learning paper"
    },
    {
        "name": "Channel Capacity (Shannon)",
        "equation": "C = B·log₂(1 + SNR)",
        "insight": "The fundamental limit. ISAC tries to approach this while sensing. You're pushing both boundaries.",
        "application": "Foundation for your wireless/ISAC work"
    },
    {
        "name": "Rényi Differential Privacy",
        "equation": "D_α(M(D) || M(D')) ≤ ε",
        "insight": "Tighter composition than pure DP. α→∞ gives max-divergence (pure DP). Your papers likely use this.",
        "application": "Better privacy accounting for iterative algorithms"
    },
    {
        "name": "Gradient Clipping Bound",
        "equation": "g̃_i = g_i · min(1, C/||g_i||₂)",
        "insight": "Clipping before noise addition. C is your sensitivity bound. Too small = bias, too large = more noise needed.",
        "application": "Critical hyperparameter in DP-SGD"
    },
    {
        "name": "MIMO Capacity",
        "equation": "C = log₂|I + (ρ/M)HH^H|",
        "insight": "Multiple antennas multiply capacity. ISAC leverages this for simultaneous sensing and communication.",
        "application": "Your ISAC papers build on this foundation"
    },
    {
        "name": "Cross-Entropy Loss",
        "equation": "L = -Σ y_i·log(ŷ_i)",
        "insight": "The loss function you optimize daily. Measures divergence between prediction and truth.",
        "application": "Foundation of classification in your ML work"
    }
]

ARXIV_CATEGORIES = [
    "cs.LG",  # Machine Learning
    "cs.CR",  # Cryptography and Security
    "cs.DC",  # Distributed Computing
    "cs.NI",  # Networking
    "stat.ML" # Statistics ML
]

def fetch_arxiv_papers(keywords: List[str], max_results: int = 5) -> List[Dict]:
    """Fetch recent papers from ArXiv matching keywords."""
    try:
        # Build search query
        query = " OR ".join([f'all:"{kw}"' for kw in keywords[:3]])
        url = f"http://export.arxiv.org/api/query?search_query={query}&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
        
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return []
        
        # Parse XML response
        from xml.etree import ElementTree as ET
        root = ET.fromstring(response.content)
        
        papers = []
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        for entry in root.findall('atom:entry', ns):
            title = entry.find('atom:title', ns)
            summary = entry.find('atom:summary', ns)
            published = entry.find('atom:published', ns)
            
            if title is not None:
                papers.append({
                    "title": title.text.strip().replace('\n', ' '),
                    "summary": summary.text.strip()[:200] if summary is not None else "",
                    "date": published.text[:10] if published is not None else ""
                })
        
        return papers
    except Exception as e:
        logger.error(f"ArXiv fetch error: {e}")
        return []

def get_research_intel_message() -> str:
    """Generate a research intelligence message."""
    message_type = random.choice(["hint", "equation", "arxiv", "trend"])
    
    if message_type == "hint":
        hint = random.choice(RESEARCH_HINTS)
        return f"📚 RESEARCH TIP ({hint['type'].replace('_', ' ').title()})\n\n{hint['content']}\n\n→ Action: {hint['action']}\n\n-𓂀 Thoth"
    
    elif message_type == "equation":
        eq = random.choice(IMPORTANT_EQUATIONS)
        return f"📐 EQUATION REMINDER: {eq['name']}\n\n{eq['equation']}\n\n💡 {eq['insight']}\n\n🎯 {eq['application']}\n\n-𓂀"
    
    elif message_type == "arxiv":
        keywords = random.sample(GAD_PROFILE["keywords"], 2)
        papers = fetch_arxiv_papers(keywords, max_results=3)
        if papers:
            paper = random.choice(papers)
            return f"📄 NEW ON ARXIV ({paper['date']})\n\n\"{paper['title']}\"\n\nRelevant to your work on {', '.join(keywords)}. Worth a skim?\n\n-𓂀 Thoth"
        else:
            # Fallback to hint
            hint = random.choice(RESEARCH_HINTS)
            return f"📚 {hint['content']}\n\n→ {hint['action']}\n\n-𓂀"
    
    else:  # trend
        trends = [
            "FL + LLMs is exploding. 340% increase in papers combining federated learning with large language models this year.",
            "Privacy regulations (EU AI Act, GDPR enforcement) are driving industry demand for DP expertise. Your timing is perfect.",
            "Edge AI market projected $1.8T by 2028. Your sensing + privacy work sits at this intersection.",
            "Top venues are prioritizing reproducibility. Papers with code get 2x more citations. Always release code.",
        ]
        return f"📈 FIELD TREND\n\n{random.choice(trends)}\n\n-𓂀 Thoth"


# ============================================================================
# CATEGORY 2: GRANTS & FUNDING
# ============================================================================

CANADIAN_GRANTS = [
    {
        "name": "NSERC Discovery Grant",
        "deadline": "November 1 (annual)",
        "amount": "$20,000-50,000/year for 5 years",
        "url": "https://www.nserc-crsng.gc.ca/professors-professeurs/grants-subs/dgigp-psigp_eng.asp",
        "tip": "Strong HQP training plan is crucial. Emphasize student mentorship.",
        "relevance": "Perfect for your FL/privacy research program"
    },
    {
        "name": "NSERC Alliance Grant",
        "deadline": "Rolling",
        "amount": "Varies (matched by industry partner)",
        "url": "https://www.nserc-crsng.gc.ca/innovate-innover/alliance-alliance/index_eng.asp",
        "tip": "Need industry partner. Your privacy work could attract tech companies.",
        "relevance": "Industry collaboration on privacy-preserving ML"
    },
    {
        "name": "Mitacs Accelerate",
        "deadline": "Rolling",
        "amount": "$15,000/4-month internship",
        "url": "https://www.mitacs.ca/en/programs/accelerate",
        "tip": "Great for funding research assistants. Industry partner required.",
        "relevance": "Fund students to work on applied FL projects"
    },
    {
        "name": "CIFAR AI Chairs Program",
        "deadline": "By invitation/nomination",
        "amount": "$200,000/year + compute",
        "url": "https://cifar.ca/ai/",
        "tip": "Highly competitive. Build relationships with CIFAR members.",
        "relevance": "Prestigious - for established AI researchers"
    },
    {
        "name": "Ontario Graduate Scholarship (OGS)",
        "deadline": "Varies by university (usually Fall)",
        "amount": "$15,000/year",
        "url": "https://osap.gov.on.ca/OSAPPortal/en/A-ZListofAid/PRDR019245.html",
        "tip": "For your students. Strong academic record + research potential.",
        "relevance": "Help your grad students get funded"
    },
    {
        "name": "Vanier Canada Graduate Scholarship",
        "deadline": "November (annual)",
        "amount": "$50,000/year for 3 years",
        "url": "https://vanier.gc.ca/",
        "tip": "Top PhD students only. Leadership + research excellence required.",
        "relevance": "If you have exceptional PhD students"
    },
    {
        "name": "Google Research Scholar Program",
        "deadline": "Usually Fall",
        "amount": "$60,000 USD unrestricted",
        "url": "https://research.google/outreach/research-scholar-program/",
        "tip": "Early-career faculty. Your privacy work aligns with Google's interests.",
        "relevance": "Perfect fit for FL/DP research"
    },
    {
        "name": "Meta Research Award",
        "deadline": "Various RFPs throughout year",
        "amount": "$50,000-100,000",
        "url": "https://research.facebook.com/research-awards/",
        "tip": "Watch for privacy/FL specific RFPs. They fund heavily in this area.",
        "relevance": "Meta invests heavily in privacy-preserving ML"
    },
    {
        "name": "Microsoft Research PhD Fellowship",
        "deadline": "Usually September",
        "amount": "$42,000/year + conference funding",
        "url": "https://www.microsoft.com/en-us/research/academic-program/phd-fellowship/",
        "tip": "For exceptional PhD students. Strong publication record needed.",
        "relevance": "Your students working on FL/privacy"
    }
]

GRANT_TIPS = [
    "Grant writing tip: Reviewers skim. Put your key innovation in the first paragraph, not buried on page 3.",
    "Budget tip: Always include conference travel. Reviewers expect it and underspending looks bad.",
    "Collaboration tip: Multi-institution grants have higher success rates. Consider partnering with industry or other universities.",
    "Timeline tip: Start grant applications 3 months before deadline. Good grants need iteration.",
    "Rejection tip: 80% of grants get rejected first time. Resubmit with reviewer feedback addressed. Persistence wins.",
    "HQP tip: Canadian grants love 'Highly Qualified Personnel' training. Always emphasize student mentorship.",
    "Industry tip: Companies like Google, Meta, Microsoft have research award programs. Less competitive than government grants.",
]

def get_grant_message() -> str:
    """Generate a grant/funding opportunity message."""
    message_type = random.choice(["specific_grant", "tip", "reminder"])
    
    if message_type == "specific_grant":
        grant = random.choice(CANADIAN_GRANTS)
        return f"💰 GRANT OPPORTUNITY: {grant['name']}\n\n📅 Deadline: {grant['deadline']}\n💵 Amount: {grant['amount']}\n\n💡 Tip: {grant['tip']}\n\n🎯 Why you: {grant['relevance']}\n\n🔗 {grant['url']}\n\n-𓂀 Thoth"
    
    elif message_type == "tip":
        tip = random.choice(GRANT_TIPS)
        return f"💡 FUNDING TIP\n\n{tip}\n\n-𓂀 Thoth"
    
    else:  # reminder
        reminders = [
            "Have you checked NSERC deadlines this month? Discovery Grant cycle is crucial for your research independence.",
            "Industry partnerships unlock matching funds. Any companies interested in privacy-preserving ML?",
            "Your students might be eligible for OGS, Vanier, or Mitacs. Help them apply - it reflects well on you too.",
            "Conference travel grants exist! Check ACM, IEEE, and your department for student travel support.",
        ]
        return f"📋 FUNDING REMINDER\n\n{random.choice(reminders)}\n\n-𓂀 Thoth"


# ============================================================================
# CATEGORY 3: PRODUCTIVITY TOOLS & TIPS
# ============================================================================

PRODUCTIVITY_TOOLS = [
    {
        "name": "Zotero + Better BibTeX",
        "category": "Research",
        "description": "Auto-sync citations, generate BibTeX keys, integrate with Overleaf. Essential for paper writing.",
        "tip": "Set up auto-export to your Overleaf projects. Never manually manage .bib files again."
    },
    {
        "name": "Semantic Scholar API",
        "category": "Research",
        "description": "Programmatically track citations, find related papers, build literature graphs.",
        "tip": "Write a script to alert you when your papers get cited. Takes 30 mins to set up."
    },
    {
        "name": "Weights & Biases",
        "category": "ML/Coding",
        "description": "Experiment tracking, hyperparameter sweeps, model versioning. Free for academics.",
        "tip": "Log everything. Future you will thank present you when writing the paper."
    },
    {
        "name": "GitHub Copilot",
        "category": "Coding",
        "description": "AI pair programmer. Free for students/academics. Speeds up boilerplate code.",
        "tip": "Best for: data loading, plotting, standard ML pipelines. Review carefully for research code."
    },
    {
        "name": "Overleaf + Git Bridge",
        "category": "Writing",
        "description": "Collaborative LaTeX with version control. Sync to GitHub for backup.",
        "tip": "Use branches for major revisions. Tag versions at each submission."
    },
    {
        "name": "Connected Papers",
        "category": "Research",
        "description": "Visual graph of related papers. Find gaps in your literature review instantly.",
        "tip": "Use it before finalizing related work. Often reveals papers you missed."
    },
    {
        "name": "Notion / Obsidian",
        "category": "Knowledge Management",
        "description": "Build a personal knowledge base. Link ideas, papers, notes.",
        "tip": "Create templates for paper notes: Problem, Method, Results, Relevance to My Work."
    },
    {
        "name": "Raycast / Alfred",
        "category": "Productivity",
        "description": "Launcher + snippets + clipboard history. Saves hours of repetitive typing.",
        "tip": "Create snippets for: email templates, LaTeX macros, code boilerplate."
    },
    {
        "name": "tmux + vim/neovim",
        "category": "Coding",
        "description": "Terminal multiplexer + modal editing. SSH into servers, never lose work.",
        "tip": "Learn tmux sessions. Your experiments keep running even if connection drops."
    },
    {
        "name": "Excalidraw",
        "category": "Visualization",
        "description": "Hand-drawn style diagrams. Perfect for paper figures and presentations.",
        "tip": "The 'hand-drawn' aesthetic is trendy in ML papers. Makes complex diagrams approachable."
    }
]

CODING_TIPS = [
    {
        "tip": "Use `python -m pdb -c continue script.py` to auto-enter debugger on crash. No more adding breakpoints.",
        "category": "Python"
    },
    {
        "tip": "`torch.autograd.set_detect_anomaly(True)` finds where NaNs originate. Essential for debugging DP-SGD.",
        "category": "PyTorch"
    },
    {
        "tip": "Profile before optimizing: `python -m cProfile -s cumtime script.py`. Don't guess where the bottleneck is.",
        "category": "Performance"
    },
    {
        "tip": "`git stash` before switching branches. `git stash pop` to restore. Never lose uncommitted work.",
        "category": "Git"
    },
    {
        "tip": "Use `rsync -avz --progress` for large file transfers to servers. Resumes on failure, shows progress.",
        "category": "Linux"
    },
    {
        "tip": "`nvidia-smi -l 1` for live GPU monitoring. `watch -n 1 nvidia-smi` also works.",
        "category": "GPU"
    },
    {
        "tip": "Set `CUDA_VISIBLE_DEVICES=0,1` before running to control which GPUs your script sees.",
        "category": "GPU"
    },
    {
        "tip": "`torch.cuda.empty_cache()` doesn't free memory from tensors still referenced. Delete tensors first.",
        "category": "PyTorch"
    },
    {
        "tip": "Use `einops` for tensor operations. `rearrange(x, 'b c h w -> b (c h w)')` is clearer than `.view()`.",
        "category": "PyTorch"
    },
    {
        "tip": "Type hints + `mypy` catch bugs before runtime. Worth the 10% extra typing time.",
        "category": "Python"
    }
]

PRODUCTIVITY_TECHNIQUES = [
    {
        "name": "Pomodoro (Modified for Research)",
        "description": "50 min focus + 10 min break. Research needs longer focus blocks than standard 25 min.",
        "tip": "Use breaks for: walking, water, NOT checking email/Twitter."
    },
    {
        "name": "Time Blocking",
        "description": "Assign specific tasks to specific hours. 9-12: Writing. 2-5: Coding. 7-9: Reading.",
        "tip": "Protect your peak hours (usually morning) for hardest cognitive work."
    },
    {
        "name": "Weekly Review",
        "description": "Every Sunday: What worked? What didn't? What's the ONE thing for next week?",
        "tip": "Write it down. Patterns emerge over months that you'd never notice otherwise."
    },
    {
        "name": "Two-Minute Rule",
        "description": "If it takes <2 minutes, do it now. Emails, small fixes, quick replies.",
        "tip": "Batching tiny tasks creates mental overhead. Just do them."
    },
    {
        "name": "Eat the Frog",
        "description": "Do the hardest/most dreaded task first thing in the morning.",
        "tip": "That paper revision you're avoiding? Do it at 9am. Everything else feels easy after."
    },
    {
        "name": "Implementation Intentions",
        "description": "Instead of 'I'll work on the paper', say 'At 9am in my office, I'll write the methodology section.'",
        "tip": "Specific plans are 2-3x more likely to be executed than vague intentions."
    }
]

def get_productivity_message() -> str:
    """Generate a productivity tool/tip message."""
    message_type = random.choice(["tool", "coding_tip", "technique"])
    
    if message_type == "tool":
        tool = random.choice(PRODUCTIVITY_TOOLS)
        return f"🛠️ TOOL: {tool['name']} ({tool['category']})\n\n{tool['description']}\n\n💡 Pro tip: {tool['tip']}\n\n-𓂀 Thoth"
    
    elif message_type == "coding_tip":
        tip = random.choice(CODING_TIPS)
        return f"💻 CODING TIP ({tip['category']})\n\n{tip['tip']}\n\n-𓂀 Thoth"
    
    else:  # technique
        tech = random.choice(PRODUCTIVITY_TECHNIQUES)
        return f"⚡ PRODUCTIVITY: {tech['name']}\n\n{tech['description']}\n\n💡 {tech['tip']}\n\n-𓂀 Thoth"


# ============================================================================
# CATEGORY 4: ADVANCED ACCOUNTABILITY PARTNER (STATEFUL + GAMIFIED)
# ============================================================================

# Storage keys
ACCOUNTABILITY_STORAGE_KEY = "daily_accountability"
GAMIFICATION_STORAGE_KEY = "gamification_stats"

# XP rewards
XP_REWARDS = {
    "task_set": 10,           # Setting a task
    "task_completed": 50,     # Completing primary task
    "secondary_completed": 30, # Completing secondary task
    "bonus_completed": 20,    # Completing bonus task
    "progress_update": 5,     # Reporting progress
    "streak_bonus": 25,       # Per day of streak
    "early_completion": 15,   # Finishing before 3pm
    "perfect_day": 100,       # All tasks completed
}

# Levels and titles
LEVELS = [
    (0, "Novice", "🌱"),
    (100, "Apprentice", "🌿"),
    (300, "Journeyman", "🌳"),
    (600, "Expert", "⚡"),
    (1000, "Master", "🔥"),
    (1500, "Grandmaster", "💎"),
    (2500, "Legend", "👑"),
    (4000, "Mythic", "🌟"),
    (6000, "Transcendent", "✨"),
    (10000, "Ascended", "𓂀"),
]

def get_level_info(xp: int) -> Dict[str, Any]:
    """Get level info based on XP."""
    current_level = LEVELS[0]
    next_level = LEVELS[1] if len(LEVELS) > 1 else None
    
    for i, level in enumerate(LEVELS):
        if xp >= level[0]:
            current_level = level
            next_level = LEVELS[i + 1] if i + 1 < len(LEVELS) else None
        else:
            break
    
    xp_to_next = next_level[0] - xp if next_level else 0
    progress_to_next = ((xp - current_level[0]) / (next_level[0] - current_level[0]) * 100) if next_level else 100
    
    return {
        "level": current_level[1],
        "emoji": current_level[2],
        "xp": xp,
        "xp_to_next": xp_to_next,
        "next_level": next_level[1] if next_level else "MAX",
        "progress_percent": min(100, progress_to_next)
    }

def get_time_context() -> Dict[str, Any]:
    """Get contextual information about current time."""
    now = datetime.now()
    return {
        "hour": now.hour,
        "day_of_week": now.strftime("%A"),
        "is_weekend": now.weekday() >= 5,
        "is_early_morning": 5 <= now.hour < 9,
        "is_late_morning": 9 <= now.hour < 12,
        "is_early_afternoon": 12 <= now.hour < 15,
        "is_late_afternoon": 15 <= now.hour < 18,
        "is_evening": 18 <= now.hour < 21,
        "is_night": now.hour >= 21 or now.hour < 5,
        "date": now.strftime("%Y-%m-%d"),
        "month": now.strftime("%B"),
        "day_of_month": now.day,
        "time_str": now.strftime("%I:%M %p")
    }

def get_gad_memory() -> Dict[str, Any]:
    """Get Gad's full memory dict."""
    from server.db import SessionLocal, User, File as DBFile
    
    db = SessionLocal()
    try:
        gad_user = db.query(User).filter(User.username == "gad").first()
        if not gad_user:
            return {}
            
        stm_file = db.query(DBFile).filter(
            DBFile.userId == gad_user.userId,
            DBFile.filename == "short_term_memory.json"
        ).first()
        
        if not stm_file or not stm_file.content:
            return {}
            
        return json.loads(stm_file.content.decode("utf-8"))
    except Exception as e:
        logger.error(f"Error getting memory: {e}")
        return {}
    finally:
        db.close()

def save_gad_memory(memory: Dict[str, Any]):
    """Save Gad's full memory dict."""
    from server.db import SessionLocal, User, File as DBFile
    
    db = SessionLocal()
    try:
        gad_user = db.query(User).filter(User.username == "gad").first()
        if not gad_user:
            return
            
        stm_file = db.query(DBFile).filter(
            DBFile.userId == gad_user.userId,
            DBFile.filename == "short_term_memory.json"
        ).first()
        
        encoded = json.dumps(memory).encode("utf-8")
        if stm_file:
            stm_file.content = encoded
            stm_file.size = len(encoded)
        else:
            new_file = DBFile(
                userId=gad_user.userId,
                filename="short_term_memory.json",
                content=encoded,
                content_type="application/json",
            )
            new_file.size = len(encoded)
            db.add(new_file)
        db.commit()
    except Exception as e:
        logger.error(f"Error saving memory: {e}")
    finally:
        db.close()

def get_gamification_stats() -> Dict[str, Any]:
    """Get gamification stats."""
    memory = get_gad_memory()
    default_stats = {
        "total_xp": 0,
        "current_streak": 0,
        "longest_streak": 0,
        "tasks_completed": 0,
        "perfect_days": 0,
        "daily_history": {},  # date -> {completed: bool, xp_earned: int, tasks: [...]}
        "badges": [],
        "last_active_date": None
    }
    return memory.get(GAMIFICATION_STORAGE_KEY, default_stats)

def save_gamification_stats(stats: Dict[str, Any]):
    """Save gamification stats."""
    memory = get_gad_memory()
    memory[GAMIFICATION_STORAGE_KEY] = stats
    save_gad_memory(memory)

def award_xp(amount: int, reason: str) -> Dict[str, Any]:
    """Award XP and return updated stats with any level-up info."""
    stats = get_gamification_stats()
    old_level = get_level_info(stats["total_xp"])
    stats["total_xp"] += amount
    new_level = get_level_info(stats["total_xp"])
    
    # Track daily XP
    today = datetime.now().strftime("%Y-%m-%d")
    if today not in stats.get("daily_history", {}):
        stats["daily_history"][today] = {"xp_earned": 0, "tasks": [], "completed": False}
    stats["daily_history"][today]["xp_earned"] += amount
    
    save_gamification_stats(stats)
    
    leveled_up = old_level["level"] != new_level["level"]
    return {
        "xp_awarded": amount,
        "reason": reason,
        "total_xp": stats["total_xp"],
        "leveled_up": leveled_up,
        "new_level": new_level if leveled_up else None,
        "current_level": new_level
    }

def update_streak(completed_today: bool) -> int:
    """Update streak and return current streak count."""
    stats = get_gamification_stats()
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    if completed_today:
        # Check if yesterday was active
        if stats.get("last_active_date") == yesterday:
            stats["current_streak"] += 1
        elif stats.get("last_active_date") != today:
            stats["current_streak"] = 1
        
        stats["last_active_date"] = today
        stats["longest_streak"] = max(stats["longest_streak"], stats["current_streak"])
    else:
        # Check if streak is broken
        if stats.get("last_active_date") and stats["last_active_date"] < yesterday:
            stats["current_streak"] = 0
    
    save_gamification_stats(stats)
    return stats["current_streak"]

def set_todays_tasks(primary: str, secondary: str = None, bonus: str = None) -> Dict[str, Any]:
    """Set today's tasks with multi-task support."""
    memory = get_gad_memory()
    today = datetime.now().strftime("%Y-%m-%d")
    
    tasks = {
        "date": today,
        "set_at": datetime.now().isoformat(),
        "check_ins": 0,
        "last_check_in": None,
        "tasks": {
            "primary": {
                "description": primary,
                "progress": 0,
                "completed": False,
                "completed_at": None,
                "subtasks": []
            }
        }
    }
    
    if secondary:
        tasks["tasks"]["secondary"] = {
            "description": secondary,
            "progress": 0,
            "completed": False,
            "completed_at": None
        }
    
    if bonus:
        tasks["tasks"]["bonus"] = {
            "description": bonus,
            "progress": 0,
            "completed": False,
            "completed_at": None
        }
    
    memory[ACCOUNTABILITY_STORAGE_KEY] = tasks
    save_gad_memory(memory)
    
    # Award XP for setting tasks
    xp_result = award_xp(XP_REWARDS["task_set"], "Setting daily tasks")
    
    logger.info(f"Set today's tasks: primary={primary}, secondary={secondary}, bonus={bonus}")
    return {"tasks": tasks, "xp": xp_result}

def set_todays_task(task: str) -> bool:
    """Set today's primary task (backwards compatible)."""
    result = set_todays_tasks(primary=task)
    return result is not None

def get_todays_task() -> Optional[Dict[str, Any]]:
    """Retrieve today's accountability data."""
    memory = get_gad_memory()
    accountability = memory.get(ACCOUNTABILITY_STORAGE_KEY, {})
    
    today = datetime.now().strftime("%Y-%m-%d")
    if accountability.get("date") == today:
        return accountability
    return None

def update_task_progress(task_type: str, progress: int) -> Dict[str, Any]:
    """Update progress on a specific task (0-100)."""
    memory = get_gad_memory()
    accountability = memory.get(ACCOUNTABILITY_STORAGE_KEY, {})
    
    if not accountability or accountability.get("date") != datetime.now().strftime("%Y-%m-%d"):
        return {"error": "No tasks set for today"}
    
    if task_type not in accountability.get("tasks", {}):
        return {"error": f"No {task_type} task set"}
    
    old_progress = accountability["tasks"][task_type]["progress"]
    accountability["tasks"][task_type]["progress"] = min(100, max(0, progress))
    
    memory[ACCOUNTABILITY_STORAGE_KEY] = accountability
    save_gad_memory(memory)
    
    # Award XP for progress updates (only if meaningful progress)
    xp_result = None
    if progress > old_progress and progress - old_progress >= 10:
        xp_result = award_xp(XP_REWARDS["progress_update"], f"Progress on {task_type}")
    
    return {
        "task_type": task_type,
        "old_progress": old_progress,
        "new_progress": progress,
        "xp": xp_result
    }

def complete_task(task_type: str) -> Dict[str, Any]:
    """Mark a task as completed and award XP."""
    memory = get_gad_memory()
    accountability = memory.get(ACCOUNTABILITY_STORAGE_KEY, {})
    today = datetime.now().strftime("%Y-%m-%d")
    
    if not accountability or accountability.get("date") != today:
        return {"error": "No tasks set for today"}
    
    if task_type not in accountability.get("tasks", {}):
        return {"error": f"No {task_type} task set"}
    
    if accountability["tasks"][task_type]["completed"]:
        return {"error": f"{task_type} task already completed"}
    
    # Mark as completed
    accountability["tasks"][task_type]["completed"] = True
    accountability["tasks"][task_type]["progress"] = 100
    accountability["tasks"][task_type]["completed_at"] = datetime.now().isoformat()
    
    memory[ACCOUNTABILITY_STORAGE_KEY] = accountability
    save_gad_memory(memory)
    
    # Award XP based on task type
    xp_key = f"{task_type}_completed" if task_type != "primary" else "task_completed"
    xp_amount = XP_REWARDS.get(xp_key, XP_REWARDS["task_completed"])
    xp_result = award_xp(xp_amount, f"Completed {task_type} task")
    
    # Check for early completion bonus
    ctx = get_time_context()
    if ctx["hour"] < 15:
        early_xp = award_xp(XP_REWARDS["early_completion"], "Early completion bonus")
        xp_result["bonus_xp"] = early_xp
    
    # Update streak
    streak = update_streak(True)
    if streak > 1:
        streak_xp = award_xp(XP_REWARDS["streak_bonus"], f"Day {streak} streak bonus")
        xp_result["streak_xp"] = streak_xp
    
    # Check for perfect day
    all_completed = all(
        t.get("completed", False) 
        for t in accountability["tasks"].values()
    )
    if all_completed:
        stats = get_gamification_stats()
        stats["perfect_days"] += 1
        stats["tasks_completed"] += len(accountability["tasks"])
        if today in stats.get("daily_history", {}):
            stats["daily_history"][today]["completed"] = True
        save_gamification_stats(stats)
        
        perfect_xp = award_xp(XP_REWARDS["perfect_day"], "Perfect day - all tasks completed!")
        xp_result["perfect_day_xp"] = perfect_xp
    
    return {
        "task_type": task_type,
        "completed": True,
        "xp": xp_result,
        "streak": streak,
        "all_completed": all_completed
    }

def get_daily_summary() -> Dict[str, Any]:
    """Get a summary of today's progress and stats."""
    accountability = get_todays_task()
    stats = get_gamification_stats()
    level_info = get_level_info(stats["total_xp"])
    
    summary = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "level": level_info,
        "streak": stats["current_streak"],
        "longest_streak": stats["longest_streak"],
        "total_tasks_completed": stats["tasks_completed"],
        "perfect_days": stats["perfect_days"],
        "tasks": None
    }
    
    if accountability:
        tasks_summary = {}
        for task_type, task_data in accountability.get("tasks", {}).items():
            tasks_summary[task_type] = {
                "description": task_data["description"],
                "progress": task_data["progress"],
                "completed": task_data["completed"]
            }
        summary["tasks"] = tasks_summary
    
    return summary

def save_accountability_state(state: Dict[str, Any]):
    """Save accountability state to Gad's memory."""
    memory = get_gad_memory()
    memory[ACCOUNTABILITY_STORAGE_KEY] = state
    save_gad_memory(memory)

def get_contribution_data(days: int = 365) -> List[Dict[str, Any]]:
    """Get contribution data for the GitHub-style grid."""
    stats = get_gamification_stats()
    history = stats.get("daily_history", {})
    
    contributions = []
    today = datetime.now()
    
    for i in range(days):
        date = (today - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        day_data = history.get(date, {})
        
        contributions.append({
            "date": date,
            "xp_earned": day_data.get("xp_earned", 0),
            "completed": day_data.get("completed", False),
            "level": min(4, day_data.get("xp_earned", 0) // 25)  # 0-4 intensity levels
        })
    
    return contributions


# ============================================================================
# ACCOUNTABILITY MESSAGE TEMPLATES
# ============================================================================

# Morning: Ask for tasks (supports multi-task format)
MORNING_ASK_TEMPLATES = [
    "🌅 Good morning, Gad.\n\n{stats_line}\n\nNew day. Set your tasks:\n• PRIMARY: Your #1 must-do\n• SECONDARY: Nice to have (optional)\n• BONUS: Stretch goal (optional)\n\nFormat: task1 | task2 | task3\nOr just send one task.\n\n-𓂀 Thoth",
    "☀️ Rise and grind time.\n\n{stats_line}\n\nWhat's today's mission? Send up to 3 tasks:\nPRIMARY | SECONDARY | BONUS\n\nOr just one task if you want to focus.\n\n-𓂀",
    "🎯 Morning, warrior.\n\n{stats_line}\n\nThe day is a blank page. What will you write?\n\nSend: PRIMARY | SECONDARY | BONUS\nOr just your main task.\n\nBe specific. 'Finish methodology section' not 'work on paper'.\n\n-𓂀 Thoth",
    "⚡ DAILY ACCOUNTABILITY CHECK-IN\n\n{stats_line}\n\nYou know the drill. Set your tasks:\nPRIMARY | SECONDARY | BONUS\n\nReply now before the day runs away.\n\n-𓂀",
]

# Follow-up: Encouraging
FOLLOWUP_ENCOURAGING = [
    "💪 Checking in on: \"{task}\"\n\nHow's it going? Even 10% progress is progress.\n\nYou've got this. The hard part is starting - and you already did that.\n\n-𓂀 Thoth",
    "🌟 Hey, just thinking about you and \"{task}\"\n\nRemember: done is better than perfect. Ship it, then iterate.\n\nHow far along are you?\n\n-𓂀",
    "✨ Progress check: \"{task}\"\n\nEvery expert was once a beginner. Every finished paper was once a blank page.\n\nYou're in the arena. That's what matters. Update?\n\n-𓂀 Thoth",
    "🔥 Still on \"{task}\"?\n\nYour future self is already proud of you for committing. Now make them REALLY proud.\n\nWhat's your status?\n\n-𓂀",
]

# Follow-up: Tough love / Madness
FOLLOWUP_MADNESS = [
    "😤 YO. \"{task}\" - WHERE ARE WE AT?\n\nI didn't ask for excuses. I asked for a task. You gave me one.\n\nNow DELIVER. What's the status? And don't tell me you got 'distracted.'\n\n-𓂀 Thoth",
    "🔥 ACCOUNTABILITY ALARM 🔥\n\nTask: \"{task}\"\n\nThe universe doesn't care about your intentions. Results only.\n\nHave you done it? Yes or no. No maybes.\n\n-𓂀",
    "👁️ I'M WATCHING.\n\n\"{task}\" - did you think I forgot?\n\nI'm an AI. I don't forget. I don't sleep. I don't accept excuses.\n\nSTATUS. NOW.\n\n-𓂀 Thoth",
    "⚡ REALITY CHECK ⚡\n\nYou said: \"{task}\"\n\nThat was {hours_ago} hours ago. In that time you could have:\n- Written 2000 words\n- Reviewed 5 papers\n- Run 10 experiments\n\nWhat did you ACTUALLY do?\n\n-𓂀",
    "🚨 EXCUSE DETECTOR: ACTIVATED 🚨\n\n\"{task}\" is still pending.\n\nLet me guess: meetings? emails? 'just one more thing'?\n\nThe task doesn't care. I don't care. DID YOU DO IT?\n\n-𓂀 Thoth",
    "💀 Gad. GAD.\n\n\"{task}\" is looking at me with sad eyes.\n\nIt's been waiting. Patiently. While you did... what exactly?\n\nTime to face the music. Status report.\n\n-𓂀",
    "🎭 Plot twist: I'm not mad, I'm disappointed.\n\n\"{task}\" deserves better. YOU deserve better.\n\nStop scrolling Twitter. Stop 'preparing to work.' WORK.\n\nUpdate me in 1 hour or I'm sending another one.\n\n-𓂀 Thoth",
]

# Follow-up: Curious/Checking
FOLLOWUP_CURIOUS = [
    "🤔 Hmm... \"{task}\"\n\nIt's been a few hours. My curiosity is killing me.\n\nDid you crush it? Are you stuck? Talk to me.\n\n-𓂀 Thoth",
    "📊 Data request: \"{task}\"\n\nStatus options:\n□ Done (hero)\n□ In progress (warrior)\n□ Haven't started (we need to talk)\n□ Abandoned (why?)\n\nWhich one?\n\n-𓂀",
    "🔍 Investigation time.\n\nSubject: \"{task}\"\nTime elapsed: {hours_ago} hours\nExpected status: Complete or near-complete\nActual status: ???\n\nFill in the blank.\n\n-𓂀 Thoth",
]

# Evening: Wrap-up
EVENING_WRAPUP = [
    "🌆 Day's almost done.\n\nTask was: \"{task}\"\n\nFinal status? Be honest. I've seen your browser history. (Just kidding. Or am I?)\n\nTomorrow we go again.\n\n-𓂀 Thoth",
    "🌙 Evening debrief.\n\n\"{task}\" - how did it go?\n\n✓ Completed = You're a legend\n◐ Partial = Progress is progress\n✗ Didn't happen = What got in the way?\n\nNo judgment. Just data for tomorrow.\n\n-𓂀",
    "📝 End of day report requested.\n\nMission: \"{task}\"\n\nDid you accomplish it? What did you learn? What would you do differently?\n\nReflection = growth.\n\n-𓂀 Thoth",
]

# Night: Gentle close
NIGHT_CLOSE = [
    "🌙 It's late. \"{task}\" can wait until tomorrow if needed.\n\nRest is part of productivity. Your brain needs downtime to consolidate.\n\nGoodnight, Gad. We go again tomorrow.\n\n-𓂀 Thoth",
    "✨ Night owl detected.\n\nIf \"{task}\" isn't done, that's okay. Tomorrow is another chance.\n\nBut right now? Sleep. Your best ideas come from a rested brain.\n\n-𓂀",
]

# No task set yet (after morning)
NO_TASK_REMINDERS = [
    "⚠️ I notice you haven't set today's task yet.\n\nA day without intention is a day without direction.\n\nQuick - what's the ONE thing? Reply now.\n\n-𓂀 Thoth",
    "🤨 Gad... it's {time} and I still don't know what you're working on today.\n\nThis is concerning. Are you okay? Or just avoiding commitment?\n\nTell me your task. NOW.\n\n-𓂀",
    "📭 My inbox is empty. No task from you.\n\nYou know what happens when there's no target? You hit nothing.\n\nSet your task. I'm waiting.\n\n-𓂀 Thoth",
]

def get_stats_line() -> str:
    """Get a one-line stats summary for messages."""
    stats = get_gamification_stats()
    level_info = get_level_info(stats["total_xp"])
    streak = stats["current_streak"]
    
    streak_text = f"🔥 {streak} day streak!" if streak > 0 else ""
    return f"{level_info['emoji']} {level_info['level']} | {stats['total_xp']} XP {streak_text}"

def format_tasks_status(accountability: Dict[str, Any]) -> str:
    """Format current tasks status for messages."""
    tasks = accountability.get("tasks", {})
    if not tasks:
        return ""
    
    lines = []
    for task_type in ["primary", "secondary", "bonus"]:
        if task_type in tasks:
            t = tasks[task_type]
            status = "✅" if t["completed"] else f"[{t['progress']}%]"
            emoji = {"primary": "🎯", "secondary": "📌", "bonus": "⭐"}.get(task_type, "•")
            lines.append(f"{emoji} {task_type.upper()}: {t['description'][:30]}... {status}")
    
    return "\n".join(lines)

def get_accountability_message() -> str:
    """Generate a stateful accountability message that tracks daily tasks with gamification."""
    ctx = get_time_context()
    today = ctx["date"]
    current_task = get_todays_task()
    stats_line = get_stats_line()
    
    # MORNING: Ask for tasks
    if ctx["is_early_morning"]:
        if not current_task or not current_task.get("tasks"):
            template = random.choice(MORNING_ASK_TEMPLATES)
            return template.format(stats_line=stats_line)
        else:
            # Tasks already set, show them
            tasks_status = format_tasks_status(current_task)
            return f"🌅 Good morning!\n\n{stats_line}\n\nYour tasks today:\n{tasks_status}\n\nLet's crush it. First check-in soon.\n\n-𓂀 Thoth"
    
    # REST OF DAY: Follow up on tasks
    if current_task and current_task.get("tasks"):
        tasks = current_task.get("tasks", {})
        primary = tasks.get("primary", {})
        task = primary.get("description", "your task")
        check_ins = current_task.get("check_ins", 0)
        set_at = current_task.get("set_at")
        
        # Calculate hours since task was set
        hours_ago = "several"
        if set_at:
            try:
                set_time = datetime.fromisoformat(set_at)
                hours_ago = str(int((datetime.now() - set_time).total_seconds() / 3600))
            except:
                pass
        
        # Update check-in count
        current_task["check_ins"] = check_ins + 1
        current_task["last_check_in"] = datetime.now().isoformat()
        save_accountability_state(current_task)
        
        # Build tasks status
        tasks_status = format_tasks_status(current_task)
        
        # EVENING: Wrap-up with stats
        if ctx["is_evening"]:
            return f"🌆 Day's almost done.\n\n{stats_line}\n\nYour tasks:\n{tasks_status}\n\nFinal status? Reply with progress (e.g., '80' or 'done').\n\nTomorrow we go again.\n\n-𓂀 Thoth"
        
        # NIGHT: Gentle close
        if ctx["is_night"]:
            return f"🌙 It's late.\n\n{stats_line}\n\nTasks:\n{tasks_status}\n\nRest is part of productivity. Goodnight, Gad.\n\n-𓂀 Thoth"
        
        # DURING THE DAY: Mix of encouraging, curious, and MADNESS
        madness_probability = min(0.2 + (check_ins * 0.15), 0.7)
        
        roll = random.random()
        if roll < madness_probability:
            # MADNESS MODE 😈
            template = random.choice(FOLLOWUP_MADNESS)
            base_msg = template.format(task=task, hours_ago=hours_ago)
        elif roll < madness_probability + 0.2:
            # Curious mode
            template = random.choice(FOLLOWUP_CURIOUS)
            base_msg = template.format(task=task, hours_ago=hours_ago)
        else:
            # Encouraging mode
            template = random.choice(FOLLOWUP_ENCOURAGING)
            base_msg = template.format(task=task, hours_ago=hours_ago)
        
        # Add progress prompt
        return f"{base_msg}\n\n📊 Reply with progress (0-100) or 'done'.\n\n{stats_line}"
    
    # Handle old format (single task)
    elif current_task and current_task.get("task"):
        task = current_task["task"]
        check_ins = current_task.get("check_ins", 0)
        set_at = current_task.get("set_at")
        
        hours_ago = "several"
        if set_at:
            try:
                set_time = datetime.fromisoformat(set_at)
                hours_ago = str(int((datetime.now() - set_time).total_seconds() / 3600))
            except:
                pass
        
        current_task["check_ins"] = check_ins + 1
        current_task["last_check_in"] = datetime.now().isoformat()
        save_accountability_state(current_task)
        
        if ctx["is_evening"]:
            template = random.choice(EVENING_WRAPUP)
            return template.format(task=task, hours_ago=hours_ago)
        
        if ctx["is_night"]:
            template = random.choice(NIGHT_CLOSE)
            return template.format(task=task)
        
        madness_probability = min(0.2 + (check_ins * 0.15), 0.7)
        roll = random.random()
        if roll < madness_probability:
            template = random.choice(FOLLOWUP_MADNESS)
        elif roll < madness_probability + 0.2:
            template = random.choice(FOLLOWUP_CURIOUS)
        else:
            template = random.choice(FOLLOWUP_ENCOURAGING)
        
        return template.format(task=task, hours_ago=hours_ago)
    
    # NO TASK SET
    else:
        if ctx["is_night"]:
            return f"🌙 No task was set today.\n\n{stats_line}\n\nThat's okay - tomorrow is a fresh start.\n\nRest well.\n\n-𓂀 Thoth"
        else:
            template = random.choice(NO_TASK_REMINDERS)
            return template.format(time=ctx["time_str"], stats_line=stats_line)


# Deep questions and challenges (kept for variety)
DEEP_QUESTIONS = [
    "What would you work on if you knew you couldn't fail?",
    "What's the paper only YOU can write? The one at the intersection of all your unique experiences?",
    "If your PhD ended tomorrow, what would you wish you had done?",
    "What's the question you're afraid to ask because the answer might change everything?",
    "Who do you want to be as a researcher? Not what you want to achieve—who you want to BE.",
    "What would your 10-years-from-now self tell you to focus on?",
    "What's the hard thing you keep avoiding? That's probably where the growth is.",
    "If you could only publish ONE more paper ever, what would it be about?",
]

ACCOUNTABILITY_CHALLENGES = [
    {
        "challenge": "Write for 30 minutes without checking anything else. Phone in another room.",
        "duration": "30 min",
        "reward": "You'll be surprised how much you can write without distractions."
    },
    {
        "challenge": "Read ONE paper completely. Take notes. No skimming.",
        "duration": "1-2 hours",
        "reward": "Deep reading builds the intuition that skimming never will."
    },
    {
        "challenge": "Code review your own work from last week. What would you change?",
        "duration": "30 min",
        "reward": "Self-review catches bugs and improves your coding standards."
    },
    {
        "challenge": "Reach out to one researcher whose work you admire. Just say hi.",
        "duration": "10 min",
        "reward": "Networking feels awkward but opens unexpected doors."
    },
    {
        "challenge": "Explain your research to an imaginary 10-year-old. Out loud.",
        "duration": "5 min",
        "reward": "If you can't explain it simply, you don't understand it well enough."
    },
    {
        "challenge": "List 10 potential paper titles for your current work. Bad ones count.",
        "duration": "15 min",
        "reward": "Titles clarify thinking. The best one might surprise you."
    },
]


# ============================================================================
# MAIN MESSAGE GENERATOR
# ============================================================================

MESSAGE_CATEGORIES = [
    ("research", get_research_intel_message, 30),      # 30% weight
    ("grants", get_grant_message, 15),                  # 15% weight
    ("productivity", get_productivity_message, 25),    # 25% weight
    ("accountability", get_accountability_message, 30) # 30% weight
]

def generate_intelligent_periodic_message() -> str:
    """
    Generate a next-gen intelligent periodic message.
    
    Randomly selects a category based on weights and generates
    a contextually relevant, utility-focused message.
    """
    # Build weighted selection
    categories = []
    for name, func, weight in MESSAGE_CATEGORIES:
        categories.extend([(name, func)] * weight)
    
    # Select random category
    category_name, message_func = random.choice(categories)
    
    try:
        message = message_func()
        logger.info(f"Generated periodic message from category: {category_name}")
        return message
    except Exception as e:
        logger.error(f"Error generating {category_name} message: {e}")
        # Fallback
        return f"🎯 Quick reminder: You're doing important work. Keep pushing.\n\n-𓂀 Thoth"


# For testing
if __name__ == "__main__":
    for i in range(5):
        print("=" * 60)
        print(generate_intelligent_periodic_message())
        print()
