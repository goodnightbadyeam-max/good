// FAQ Toggle
document.addEventListener('DOMContentLoaded', function() {
    const faqItems = document.querySelectorAll('.faq-item');
    
    faqItems.forEach(item => {
        const question = item.querySelector('.faq-question');
        
        question.addEventListener('click', () => {
            const isActive = item.classList.contains('active');
            
            // Close all items
            faqItems.forEach(faqItem => {
                faqItem.classList.remove('active');
            });
            
            // Toggle current item
            if (!isActive) {
                item.classList.add('active');
            }
        });
    });
    
    // Smooth scrolling for navigation links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // Language selector
    const langButtons = document.querySelectorAll('.lang-btn');
    
    langButtons.forEach(button => {
        button.addEventListener('click', () => {
            langButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
        });
    });
    
    // Animated counter for stats
    function animateCounter(element, target, duration = 2000, isPercentage = false, isTime = false) {
        let start = 0;
        const increment = target / (duration / 16);
        const timer = setInterval(() => {
            start += increment;
            if (start >= target) {
                start = target;
                clearInterval(timer);
            }
            
            if (isTime) {
                element.textContent = '24/7';
            } else if (isPercentage) {
                element.textContent = start.toFixed(1) + '%';
            } else {
                element.textContent = Math.floor(start).toLocaleString() + '+';
            }
        }, 16);
    }
    
    // Intersection Observer for stats animation
    const statsObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && !entry.target.classList.contains('animated')) {
                entry.target.classList.add('animated');
                const statNumbers = entry.target.querySelectorAll('.stat-number');
                
                statNumbers.forEach((stat, index) => {
                    const text = stat.textContent.trim();
                    
                    if (text.includes('15000')) {
                        animateCounter(stat, 15000, 2000);
                    } else if (text.includes('5000')) {
                        animateCounter(stat, 5000, 2000);
                    } else if (text.includes('99.9')) {
                        animateCounter(stat, 99.9, 2000, true);
                    } else if (text.includes('24/7')) {
                        stat.textContent = '24/7';
                    }
                });
            }
        });
    }, { threshold: 0.5 });
    
    const statsBanner = document.querySelector('.stats-banner');
    if (statsBanner) {
        statsObserver.observe(statsBanner);
    }
    
    // Universal Intersection Observer for all fade-in animations
    const fadeInObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                if (entry.target.classList.contains('animate-header')) {
                    entry.target.classList.add('visible');
                } else {
                    entry.target.classList.add('fade-in');
                }
            }
        });
    }, { threshold: 0.1 });
    
    // Observe gift cards
    const giftCards = document.querySelectorAll('.gift-card');
    giftCards.forEach(card => {
        fadeInObserver.observe(card);
    });
    
    // Observe advantage cards (with animate-in class)
    const advantageCards = document.querySelectorAll('.advantage-card');
    advantageCards.forEach(card => {
        card.classList.add('animate-in');
        fadeInObserver.observe(card);
    });
    
    // Observe process steps (with animate-in class)
    const processSteps = document.querySelectorAll('.process-step');
    processSteps.forEach(step => {
        step.classList.add('animate-in');
        fadeInObserver.observe(step);
    });
    
    // Observe FAQ items (with animate-in class)
    const faqItemsForAnimation = document.querySelectorAll('.faq-item');
    faqItemsForAnimation.forEach(item => {
        item.classList.add('animate-in');
        fadeInObserver.observe(item);
    });
    
    // Observe section headers
    const sectionHeaders = document.querySelectorAll('.section-header');
    sectionHeaders.forEach(header => {
        header.classList.add('section-fade-in', 'animate-header');
        fadeInObserver.observe(header);
    });
});


// Мультиязычность
const translations = {
    ru: {
        // Header
        home: 'Главная',
        catalog: 'Каталог',
        advantages: 'Преимущества',
        faq: 'FAQ',
        contacts: 'Контакты',
        loginBtn: 'Войти через Telegram',
        
        // Hero
        heroTitle: 'Надёжный сервис сделок с Telegram Gifts',
        heroText: 'LZMarket проводит сделки с подарками через эскроу: средства и NFT блокируются до подтверждения обеими сторонами. Безопасно, честно и без риска.',
        startDeal: 'Начать сделку',
        happyClients: 'довольных клиентов',
        
        // Gifts
        giftsLabel: 'ПОДАРКИ',
        giftsTitle: 'Гарантируем любые Telegram Gifts',
        giftsText: 'Проводим сделки с коллекционными подарками под защитой гаранта',
        underGuarantee: 'Под гарантом',
        collectible: 'Collectible',
        
        // Advantages
        advLabel: 'ПОЧЕМУ МЫ',
        advTitle: 'Преимущества сервиса',
        adv1Title: 'Мгновенная доставка',
        adv1Text: 'Подарки придут за секунды после оплаты — без ожидания.',
        adv2Title: 'Безопасные сделки',
        adv2Text: 'Гарант и эскроу защищают каждую сделку на всех этапах.',
        adv3Title: '1000+ клиентов',
        adv3Text: 'Репутация, проверенная тысячами успешных сделок.',
        adv4Title: 'Только оригиналы',
        adv4Text: 'Настоящие Telegram Gifts, каждый проходит на подлинность.',
        
        // Process
        processLabel: 'ПРОЦЕСС',
        processTitle: 'Как это работает',
        step1Title: 'Создайте сделку',
        step1Text: 'Запустите бота и укажите условия обмена.',
        step2Title: 'Гарант блокирует',
        step2Text: 'Средства и подарок в надёжном эскроу.',
        step3Title: 'Обмен подарками',
        step3Text: 'Стороны передают NFT под контролем бота.',
        step4Title: 'Гарант завершает',
        step4Text: 'Сделка закрыта, обе стороны довольны.',
        stat1Label: 'Успешных сделок',
        stat2Label: 'Клиентов',
        stat3Label: 'Успешных доставок',
        stat4Label: 'Поддержка',
        
        // FAQ
        faqLabel: 'FAQ',
        faqTitle: 'Частые вопросы',
        faq1Q: 'Что такое Telegram Gifts?',
        faq1A: 'Это коллекционные цифровые подарки в Telegram, которые можно дарить, покупать и обменивать между пользователями.',
        faq2Q: 'Как проходит сделка?',
        faq2A: 'Через встроенный гарант-эскроу: средства и подарок блокируются до подтверждения обеими сторонами, поэтому обмен исключён.',
        faq3Q: 'Какие способы оплаты доступны?',
        faq3A: 'Оплата в TON и Telegram Stars. Средства и подарки зачисляются мгновенно после подтверждения.',
        faq4Q: 'Это действительно безопасно?',
        faq4A: 'Да. Каждая сделка защищена эскроу, а все подарки проходят проверку на оригинальность перед продажей.',
        faq5Q: 'Как связаться с поддержкой?',
        faq5A: 'Напишите нам прямо в Telegram — команда поддержки на связи 24/7 и отвечает в течение нескольких минут.',
        
        // Footer
        footerText: 'Промышленный маркет Telegram Gifts. Быстро, безопасно и с гарантией на каждую сделку.',
        navTitle: 'Навигация',
        helpTitle: 'Помощь',
        telegram: 'Telegram',
        support: 'Поддержка',
        policy: 'Политика',
        rules: 'Правила',
        copyright: '© 2024 LZMarket. Все права защищены.'
    },
    en: {
        // Header
        home: 'Home',
        catalog: 'Catalog',
        advantages: 'Advantages',
        faq: 'FAQ',
        contacts: 'Contacts',
        loginBtn: 'Log in with Telegram',
        
        // Hero
        heroTitle: 'A trusted service for Telegram Gifts deals',
        heroText: 'LZMarket runs gift deals through escrow: funds and NFTs stay locked until both sides confirm. Safe, fair and risk-free.',
        startDeal: 'Start a deal',
        happyClients: 'happy clients',
        
        // Gifts
        giftsLabel: 'GIFTS',
        giftsTitle: 'We guarantee any Telegram Gifts',
        giftsText: 'We handle deals with collectible gifts under escrow protection',
        underGuarantee: 'Escrow protected',
        collectible: 'Collectible',
        
        // Advantages
        advLabel: 'WHY US',
        advTitle: 'Service advantages',
        adv1Title: 'Instant delivery',
        adv1Text: 'Gifts arrive within seconds of payment — no waiting.',
        adv2Title: 'Secure deals',
        adv2Text: 'Guarantor and escrow protect every deal at every stage.',
        adv3Title: '1000+ clients',
        adv3Text: 'A reputation proven by thousands of successful deals.',
        adv4Title: 'Originals only',
        adv4Text: 'Genuine Telegram Gifts, each verified for authenticity.',
        
        // Process
        processLabel: 'PROCESS',
        processTitle: 'How it works',
        step1Title: 'Create a deal',
        step1Text: 'Start the bot and set the exchange terms.',
        step2Title: 'Escrow locks',
        step2Text: 'Funds and the gift held safely in escrow.',
        step3Title: 'Exchange gifts',
        step3Text: 'Parties transfer the NFT under bot control.',
        step4Title: 'Guarantor closes',
        step4Text: 'The deal is closed, both sides satisfied.',
        stat1Label: 'Successful deals',
        stat2Label: 'Clients',
        stat3Label: 'Successful deliveries',
        stat4Label: 'Support',
        
        // FAQ
        faqLabel: 'FAQ',
        faqTitle: 'Frequently asked',
        faq1Q: 'What are Telegram Gifts?',
        faq1A: 'Collectible digital gifts in Telegram that can be gifted, bought and traded between users.',
        faq2Q: 'How does a deal work?',
        faq2A: 'Through built-in guarantor-escrow: funds and gift are locked until confirmation from both sides, so fraud is excluded.',
        faq3Q: 'What payment methods are available?',
        faq3A: 'Payment in TON and Telegram Stars. Funds and gifts are credited instantly after confirmation.',
        faq4Q: 'Is it really safe?',
        faq4A: 'Yes. Every deal is protected by escrow, and all gifts pass an authenticity check before sale.',
        faq5Q: 'How to contact support?',
        faq5A: 'Write to us directly in Telegram — support team is available 24/7 and responds within a few minutes.',
        
        // Footer
        footerText: 'A premium Telegram Gifts market. Fast, secure and guaranteed on every deal.',
        navTitle: 'Navigation',
        helpTitle: 'Help',
        telegram: 'Telegram',
        support: 'Support',
        policy: 'Policy',
        rules: 'Rules',
        copyright: '© 2024 LZMarket. All rights reserved.'
    }
};

// Функция переключения языка
function switchLanguage(lang) {
    const t = translations[lang];
    
    // Header
    document.querySelector('.nav-menu li:nth-child(1) a').textContent = t.home;
    document.querySelector('.nav-menu li:nth-child(2) a').textContent = t.catalog;
    document.querySelector('.nav-menu li:nth-child(3) a').textContent = t.advantages;
    document.querySelector('.nav-menu li:nth-child(4) a').textContent = t.faq;
    document.querySelector('.nav-menu li:nth-child(5) a').textContent = t.contacts;
    document.querySelector('.telegram-btn').childNodes[2].textContent = ' ' + t.loginBtn;
    
    // Hero
    document.querySelector('.hero-text h1').textContent = t.heroTitle;
    document.querySelector('.hero-text p').textContent = t.heroText;
    document.querySelector('.cta-button').childNodes[2].textContent = ' ' + t.startDeal;
    document.querySelector('.rating-text span').innerHTML = `<strong>1000+</strong> ${t.happyClients} · <span class="stars">⭐⭐⭐⭐⭐</span>`;
    
    // Gifts
    document.querySelectorAll('.section-label')[0].textContent = t.giftsLabel;
    document.querySelectorAll('.section-header h2')[0].textContent = t.giftsTitle;
    document.querySelectorAll('.section-header p')[0].textContent = t.giftsText;
    document.querySelectorAll('.gift-badge').forEach(badge => {
        badge.childNodes[2].textContent = ' ' + t.underGuarantee;
    });
    
    // Advantages
    document.querySelectorAll('.section-label')[1].textContent = t.advLabel;
    document.querySelectorAll('.section-header h2')[1].textContent = t.advTitle;
    document.querySelectorAll('.advantage-card h3')[0].textContent = t.adv1Title;
    document.querySelectorAll('.advantage-card p')[0].textContent = t.adv1Text;
    document.querySelectorAll('.advantage-card h3')[1].textContent = t.adv2Title;
    document.querySelectorAll('.advantage-card p')[1].textContent = t.adv2Text;
    document.querySelectorAll('.advantage-card h3')[2].textContent = t.adv3Title;
    document.querySelectorAll('.advantage-card p')[2].textContent = t.adv3Text;
    document.querySelectorAll('.advantage-card h3')[3].textContent = t.adv4Title;
    document.querySelectorAll('.advantage-card p')[3].textContent = t.adv4Text;
    
    // Process
    document.querySelectorAll('.section-label')[2].textContent = t.processLabel;
    document.querySelectorAll('.section-header h2')[2].textContent = t.processTitle;
    document.querySelectorAll('.process-step h3')[0].textContent = t.step1Title;
    document.querySelectorAll('.process-step p')[0].textContent = t.step1Text;
    document.querySelectorAll('.process-step h3')[1].textContent = t.step2Title;
    document.querySelectorAll('.process-step p')[1].textContent = t.step2Text;
    document.querySelectorAll('.process-step h3')[2].textContent = t.step3Title;
    document.querySelectorAll('.process-step p')[2].textContent = t.step3Text;
    document.querySelectorAll('.process-step h3')[3].textContent = t.step4Title;
    document.querySelectorAll('.process-step p')[3].textContent = t.step4Text;
    document.querySelectorAll('.stat-label')[0].textContent = t.stat1Label;
    document.querySelectorAll('.stat-label')[1].textContent = t.stat2Label;
    document.querySelectorAll('.stat-label')[2].textContent = t.stat3Label;
    document.querySelectorAll('.stat-label')[3].textContent = t.stat4Label;
    
    // FAQ
    document.querySelectorAll('.section-label')[3].textContent = t.faqLabel;
    document.querySelectorAll('.section-header h2')[3].textContent = t.faqTitle;
    document.querySelectorAll('.faq-question h3')[0].textContent = t.faq1Q;
    document.querySelectorAll('.faq-answer p')[0].textContent = t.faq1A;
    document.querySelectorAll('.faq-question h3')[1].textContent = t.faq2Q;
    document.querySelectorAll('.faq-answer p')[1].textContent = t.faq2A;
    document.querySelectorAll('.faq-question h3')[2].textContent = t.faq3Q;
    document.querySelectorAll('.faq-answer p')[2].textContent = t.faq3A;
    document.querySelectorAll('.faq-question h3')[3].textContent = t.faq4Q;
    document.querySelectorAll('.faq-answer p')[3].textContent = t.faq4A;
    document.querySelectorAll('.faq-question h3')[4].textContent = t.faq5Q;
    document.querySelectorAll('.faq-answer p')[4].textContent = t.faq5A;
    
    // Footer
    document.querySelector('.footer-brand p').textContent = t.footerText;
    document.querySelectorAll('.footer-column h4')[0].textContent = t.navTitle;
    document.querySelectorAll('.footer-column h4')[1].textContent = t.helpTitle;
    document.querySelectorAll('.footer-column li a')[3].textContent = t.telegram;
    document.querySelectorAll('.footer-column li a')[4].textContent = t.support;
    document.querySelectorAll('.footer-column li a')[5].textContent = t.policy;
    document.querySelectorAll('.footer-column li a')[6].textContent = t.rules;
    document.querySelector('.footer-bottom p').textContent = t.copyright;
    
    // Сохранить выбранный язык
    localStorage.setItem('language', lang);
}

// Обработчик переключения языков
document.querySelectorAll('.lang-btn').forEach((btn, index) => {
    btn.addEventListener('click', () => {
        const langs = ['ru', 'en', 'zh', 'ar'];
        const selectedLang = langs[index];
        
        // Переключаем только для RU и EN
        if (selectedLang === 'ru' || selectedLang === 'en') {
            switchLanguage(selectedLang);
        }
    });
});

// Загрузить сохраненный язык при загрузке страницы
const savedLang = localStorage.getItem('language') || 'ru';
if (savedLang === 'en') {
    // Небольшая задержка чтобы DOM полностью загрузился
    setTimeout(() => switchLanguage('en'), 100);
}


// Добавляем китайский перевод
translations.zh = {
    // Header
    home: '首页',
    catalog: '目录',
    advantages: '优势',
    faq: 'FAQ',
    contacts: '联系',
    loginBtn: '通过 Telegram 登录',
    
    // Hero
    heroTitle: '值得信赖的 Telegram Gifts 交易服务',
    heroText: 'LZMarket 通过托管完成礼物交易：资金与 NFT 在双方确认前被锁定。安全、公正、无风险。',
    startDeal: '开始交易',
    happyClients: '满意客户',
    
    // Gifts
    giftsLabel: '礼物',
    giftsTitle: '担保任何 Telegram Gifts',
    giftsText: '在担保保护下处理收藏礼物交易',
    underGuarantee: '担保保护',
    collectible: 'Collectible',
    
    // Advantages
    advLabel: '为什么选择我们',
    advTitle: '服务优势',
    adv1Title: '即时交付',
    adv1Text: '付款后数秒内到账，无需等待。',
    adv2Title: '安全交易',
    adv2Text: '担保与托管在每个阶段保护每一笔交易。',
    adv3Title: '1000+ 客户',
    adv3Text: '数千笔成功交易验证的信誉。',
    adv4Title: '仅限正品',
    adv4Text: '真正的 Telegram Gifts，每件均经过真伪验证。',
    
    // Process
    processLabel: '流程',
    processTitle: '如何运作',
    step1Title: '创建交易',
    step1Text: '启动机器人并设置交换条件。',
    step2Title: '托管锁定',
    step2Text: '资金与礼物被安全托管。',
    step3Title: '交换礼物',
    step3Text: '双方在机器人监控下转移 NFT。',
    step4Title: '担保完成',
    step4Text: '交易完成，双方满意。',
    stat1Label: '成功交易',
    stat2Label: '客户',
    stat3Label: '成功交付',
    stat4Label: '支援',
    
    // FAQ
    faqLabel: '常见问题',
    faqTitle: '常见问题',
    faq1Q: '什么是 Telegram Gifts？',
    faq1A: 'Telegram 中的收藏数字礼物，可以在用户之间赠送、购买和交易。',
    faq2Q: '交易如何进行？',
    faq2A: '通过内置担保托管：资金和礼物被锁定直到双方确认，因此排除了欺诈。',
    faq3Q: '有哪些付款方式？',
    faq3A: '支持 TON 和 Telegram Stars 付款。确认后资金和礼物即时到账。',
    faq4Q: '真的安全吗？',
    faq4A: '是的。每笔交易都受托管保护，所有礼物在销售前都会通过真伪检查。',
    faq5Q: '如何联系支持？',
    faq5A: '直接在 Telegram 中给我们写信 — 支持团队全天候在线，几分钟内回复。',
    
    // Footer
    footerText: '高端 Telegram Gifts 市场。快速、安全，每笔交易均有保证。',
    navTitle: '导航',
    helpTitle: '帮助',
    telegram: 'Telegram',
    support: '支持',
    policy: '政策',
    rules: '规则',
    copyright: '© 2024 LZMarket. 版权所有。'
};

// Обновляем обработчик для поддержки китайского языка
const originalLangHandler = document.querySelectorAll('.lang-btn');
originalLangHandler.forEach((btn, index) => {
    const langs = ['ru', 'en', 'zh', 'ar'];
    const selectedLang = langs[index];
    
    // Добавляем обработчик для китайского
    if (selectedLang === 'zh') {
        btn.addEventListener('click', () => {
            switchLanguage('zh');
        });
    }
});

// Проверяем сохраненный китайский язык
const currentLang = localStorage.getItem('language');
if (currentLang === 'zh') {
    setTimeout(() => switchLanguage('zh'), 100);
}


// Добавляем арабский перевод
translations.ar = {
    // Header
    home: 'الرئيسية',
    catalog: 'الكتالوج',
    advantages: 'المزايا',
    faq: 'الأسئلة',
    contacts: 'اتصل',
    loginBtn: 'تسجيل الدخول عبر Telegram',
    
    // Hero
    heroTitle: 'خدمة موثوقة لصفقات Telegram Gifts',
    heroText: 'تجري LZMarket صفقات الهدايا عبر الضمان: تُحفظ الأموال و NFT حتى يؤكد الطرفان. آمن وعادل وبدون مخاطر.',
    startDeal: 'ابدأ الصفقة',
    happyClients: 'عميل سعيد',
    
    // Gifts
    giftsLabel: 'الهدايا',
    giftsTitle: 'نضمن أي Telegram Gifts',
    giftsText: 'نُجري صفقات الهدايا المُحتفظة تحت حماية الضمان',
    underGuarantee: 'محمي بالضمان',
    collectible: 'Collectible',
    
    // Advantages
    advLabel: 'لماذا نحن',
    advTitle: 'مزايا الخدمة',
    adv1Title: 'تسليم فوري',
    adv1Text: 'تصل الهدايا خلال ثوان من الدفع — دون انتظار.',
    adv2Title: 'صفقات آمنة',
    adv2Text: 'الضامن والضمان يحميان كل صفقة في كل مرحلة.',
    adv3Title: 'أكثر من 1000 عميل',
    adv3Text: 'سمعة أثبتتها آلاف الصفقات الناجحة.',
    adv4Title: 'أصلية فقط',
    adv4Text: 'هدايا Telegram حقيقية، تم التحقق من صحة كل منها.',
    
    // Process
    processLabel: 'العملية',
    processTitle: 'كيف تعمل',
    step1Title: 'أنشئ صفقة',
    step1Text: 'شغّل البوت وحدّد شروط التبادل.',
    step2Title: 'يقفل الضمان',
    step2Text: 'الأموال والهدية محفوظة بأمان في الضمان.',
    step3Title: 'تبادل الهدايا',
    step3Text: 'يحول الطرفان الـ NFT تحت سيطرة البوت.',
    step4Title: 'ينهي الضامن',
    step4Text: 'أُغلقت الصفقة، راضٍ الطرفان.',
    stat1Label: 'صفقات ناجحة',
    stat2Label: 'عملاء',
    stat3Label: 'عمليات تسليم ناجحة',
    stat4Label: 'دعم',
    
    // FAQ
    faqLabel: 'الأسئلة',
    faqTitle: 'الأسئلة الشائعة',
    faq1Q: 'ما هي Telegram Gifts؟',
    faq1A: 'هدايا رقمية قابلة للتحصيل في Telegram يمكن إهداؤها وشراؤها وتداولها بين المستخدمين.',
    faq2Q: 'كيف تعمل الصفقة؟',
    faq2A: 'من خلال ضامن-ضمان مُدمج: تُقفل الأموال والهدية حتى يؤكد الطرفان، لذا الاحتيال مستبعد.',
    faq3Q: 'ما هي طرق الدفع المتاحة؟',
    faq3A: 'الدفع بـ TON و Telegram Stars. تُضاف الأموال والهدايا فوراً بعد التأكيد.',
    faq4Q: 'هل هو آمن حقاً؟',
    faq4A: 'نعم. كل صفقة محمية بالضمان، وجميع الهدايا تمر بفحص الأصالة قبل البيع.',
    faq5Q: 'كيف أتواصل مع الدعم؟',
    faq5A: 'اكتب لنا مباشرة في Telegram — فريق الدعم متاح على مدار الساعة ويرد في غضون دقائق.',
    
    // Footer
    footerText: 'سوق Telegram Gifts متميز. سريع وآمن ومضمون في كل صفقة.',
    navTitle: 'التنقل',
    helpTitle: 'مساعدة',
    telegram: 'Telegram',
    support: 'دعم',
    policy: 'سياسة',
    rules: 'قواعد',
    copyright: '© 2024 LZMarket. جميع الحقوق محفوظة.'
};

// Обновляем обработчик для поддержки арабского языка
document.querySelectorAll('.lang-btn').forEach((btn, index) => {
    const langs = ['ru', 'en', 'zh', 'ar'];
    const selectedLang = langs[index];
    
    btn.addEventListener('click', () => {
        if (translations[selectedLang]) {
            switchLanguage(selectedLang);
            
            // Для арабского добавляем RTL
            if (selectedLang === 'ar') {
                document.documentElement.setAttribute('dir', 'rtl');
                document.body.style.fontFamily = 'Arial, sans-serif';
            } else {
                document.documentElement.setAttribute('dir', 'ltr');
                document.body.style.fontFamily = '-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", sans-serif';
            }
        }
    });
});

// Проверяем сохраненный арабский язык
const currentLanguage = localStorage.getItem('language');
if (currentLanguage === 'ar') {
    setTimeout(() => {
        switchLanguage('ar');
        document.documentElement.setAttribute('dir', 'rtl');
        document.body.style.fontFamily = 'Arial, sans-serif';
    }, 100);
}


async function loadPublicConfig(){try{const r=await fetch('/api/config',{cache:'no-store'});if(!r.ok)return;const c=await r.json();document.querySelectorAll('[data-manager-link]').forEach(a=>a.href=c.manager_url);}catch(e){}}
document.addEventListener('DOMContentLoaded',loadPublicConfig);
