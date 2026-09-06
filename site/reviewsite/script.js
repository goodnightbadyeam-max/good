// Telegram Web App API
let tg = window.Telegram.WebApp;
tg.expand();

// Получаем данные пользователя из Telegram
const telegramUser = tg.initDataUnsafe.user;
const username = telegramUser ? telegramUser.username || telegramUser.first_name : 'Guest';

// Подписанная строка: только по ней сервер понимает, кто пришёл.
// В браузере без Telegram она пустая — форма и свои отзывы будут недоступны.
const initData = tg.initData || '';

// Право на отзыв выдаёт сервер, здесь только рисуем результат.
let profile = { authorized: false, canReview: false, deals: 0, required: 2 };

function authHeaders(extra) {
    return Object.assign({ 'X-Telegram-Init-Data': initData }, extra || {});
}

// Переводы
const translations = {
    ru: {
        reviewTitle: 'Как оставить отзыв?',
        step1: '1. Выберите оценку (1-5)',
        step2: '2. Выберите подарок который вы продали/купили',
        step3: '3. Напишите мини коментарий',
        ratingLabel: 'Оценка',
        nicknameLabel: 'Ник',
        giftLabel: 'Подарок',
        giftPlaceholder: 'Выбрать подарок',
        textLabel: 'Текст',
        textPlaceholder: 'как прошла сделка в боте',
        submitButton: 'Опубликовать',
        allReviews: 'Все отзывы',
        reviewsShown: 'Вам показаны',
        reviewsOf: 'отзывов из',
        charLimit: '/ максимум 50 символов',
        reviews: 'отзывов',
        gateNeedDeals: 'Отзыв можно оставить после {required} завершённых сделок. У вас сейчас: {deals}.',
        gateNoAuth: 'Откройте страницу через бота, чтобы оставить отзыв.',
        gateError: 'Не удалось проверить ваши сделки. Попробуйте позже.'
    },
    en: {
        reviewTitle: 'How to leave a review?',
        step1: '1. Select rating (1-5)',
        step2: '2. Select the gift you sold/bought',
        step3: '3. Write a mini comment',
        ratingLabel: 'Rating',
        nicknameLabel: 'Nickname',
        giftLabel: 'Gift',
        giftPlaceholder: 'Select gift',
        textLabel: 'Text',
        textPlaceholder: 'how the deal went',
        submitButton: 'Submit',
        allReviews: 'All reviews',
        reviewsShown: 'Showing',
        reviewsOf: 'reviews out of',
        charLimit: '/ max 50 characters',
        reviews: 'reviews',
        gateNeedDeals: 'You can leave a review after {required} completed deals. You have {deals}.',
        gateNoAuth: 'Open this page from the bot to leave a review.',
        gateError: 'Could not check your deals. Please try again later.'
    },
    zh: {
        reviewTitle: '如何留下评论？',
        step1: '1. 选择评分 (1-5)',
        step2: '2. 选择您出售/购买的礼物',
        step3: '3. 写一条简短评论',
        ratingLabel: '评分',
        nicknameLabel: '昵称',
        giftLabel: '礼物',
        giftPlaceholder: '选择礼物',
        textLabel: '文本',
        textPlaceholder: '交易进展如何',
        submitButton: '提交',
        allReviews: '所有评论',
        reviewsShown: '显示',
        reviewsOf: '条评论，共',
        charLimit: '/ 最多50个字符',
        reviews: '条评论',
        gateNeedDeals: '完成 {required} 笔交易后即可留下评论。您目前有 {deals} 笔。',
        gateNoAuth: '请通过机器人打开此页面以留下评论。',
        gateError: '无法核对您的交易，请稍后再试。'
    },
    ar: {
        reviewTitle: 'كيفية ترك تقييم؟',
        step1: '1. اختر التقييم (1-5)',
        step2: '2. اختر الهدية التي بعتها/اشتريتها',
        step3: '3. اكتب تعليقًا صغيرًا',
        ratingLabel: 'التقييم',
        nicknameLabel: 'الاسم',
        giftLabel: 'الهدية',
        giftPlaceholder: 'اختر الهدية',
        textLabel: 'النص',
        textPlaceholder: 'كيف سارت الصفقة',
        submitButton: 'نشر',
        allReviews: 'جميع التقييمات',
        reviewsShown: 'يتم عرض',
        reviewsOf: 'تقييمًا من',
        charLimit: '/ بحد أقصى 50 حرفًا',
        reviews: 'تقييمات',
        gateNeedDeals: 'يمكنك ترك تقييم بعد {required} صفقات مكتملة. لديك الآن {deals}.',
        gateNoAuth: 'افتح هذه الصفحة من خلال البوت لترك تقييم.',
        gateError: 'تعذر التحقق من صفقاتك. حاول لاحقًا.'
    }
};

let currentLang = 'ru';

function updateLanguage(lang) {
    currentLang = lang;
    const t = translations[lang];
    
    // Обновляем направление текста для арабского
    if (lang === 'ar') {
        document.body.setAttribute('dir', 'rtl');
        document.documentElement.setAttribute('lang', 'ar');
    } else {
        document.body.setAttribute('dir', 'ltr');
        document.documentElement.setAttribute('lang', lang);
    }
    
    // Обновляем текст на странице
    document.querySelector('.form-title').textContent = t.reviewTitle;
    document.querySelectorAll('.form-instructions p')[0].textContent = t.step1;
    document.querySelectorAll('.form-instructions p')[1].textContent = t.step2;
    document.querySelectorAll('.form-instructions p')[2].textContent = t.step3;
    
    document.querySelectorAll('.form-group label')[0].textContent = t.ratingLabel;
    document.querySelectorAll('.form-group label')[1].textContent = t.nicknameLabel;
    document.querySelectorAll('.form-group label')[2].textContent = t.giftLabel;
    document.querySelectorAll('.form-group label')[3].textContent = t.textLabel;
    
    document.getElementById('gift-select-text').textContent = t.giftPlaceholder;
    document.getElementById('text-input').placeholder = t.textPlaceholder;
    document.querySelector('.submit-button').textContent = t.submitButton;
    
    document.querySelector('.reviews-header h3').textContent = t.allReviews;
    
    // Обновляем rating-total с реальным количеством
    const totalCount = document.getElementById('total-reviews-count').textContent;
    document.querySelector('.rating-total').innerHTML = `<span id="total-reviews-count">${totalCount}</span> ${t.reviews}`;
    
    // Обновляем футер
    const footerText = document.querySelector('.reviews-footer p');
    const shownCount = document.getElementById('shown-reviews-count').textContent;
    const totalCountFooter = document.getElementById('footer-total-count').textContent;
    footerText.innerHTML = `${t.reviewsShown} <span id="shown-reviews-count">${shownCount}</span> ${t.reviewsOf} <span id="footer-total-count">${totalCountFooter}</span>`;
    
    // Обновляем счётчик символов
    const charCounter = document.querySelector('.char-counter');
    const currentCount = document.getElementById('char-count').textContent;
    charCounter.innerHTML = `<span id="char-count">${currentCount}</span> ${t.charLimit}`;

    applyReviewGate();
}

// Пустая строка = отзыв оставлять можно.
function gateMessage() {
    const t = translations[currentLang] || translations.ru;
    if (profile.error) return t.gateError;
    if (!profile.authorized) return t.gateNoAuth;
    if (!profile.canReview) {
        return t.gateNeedDeals
            .replace('{required}', profile.required)
            .replace('{deals}', profile.deals);
    }
    return '';
}

function applyReviewGate() {
    const notice = document.getElementById('review-gate');
    const button = document.querySelector('.submit-button');
    const form = document.querySelector('.review-form');
    if (!notice || !button || !form) return;

    const message = gateMessage();
    notice.textContent = message;
    notice.hidden = !message;
    button.disabled = Boolean(message);
    form.classList.toggle('review-form--locked', Boolean(message));
}

async function loadProfile() {
    const defaults = { authorized: false, canReview: false, deals: 0, required: 2 };
    try {
        const response = await fetch('/api/me', { headers: authHeaders() });
        profile = Object.assign({}, defaults, await response.json());
    } catch (error) {
        console.error('Failed to load profile:', error);
        profile = Object.assign({}, defaults, { error: 'network' });
    }
    applyReviewGate();
}

// Scroll animations
function observeElements() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry, index) => {
            if (entry.isIntersecting) {
                // Добавляем задержку для каскадного эффекта
                setTimeout(() => {
                    entry.target.classList.add('show');
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }, index * 50);
            }
        });
    }, {
        threshold: 0.05,
        rootMargin: '0px 0px -30px 0px'
    });

    // Наблюдаем за элементами
    document.querySelectorAll('.rating-statistics, .review-form, .review-item, .reviews-footer').forEach(el => {
        observer.observe(el);
    });
}

// Total reviews count - REAL COUNT (starts at 100, matches reviewsData length)
let totalReviewsCount = 100; // Реальное количество отзывов в reviewsData

// Gift items list
const giftItems = [
    "Jack-in-the-Box", "Mighty Arm", "B-Day Candle", "Flying Broom", "Star Notepad",
    "Moon Pendant", "Ginger Cookie", "Witch Hat", "Joyful Bundle", "Restless Jar",
    "Hanging Star", "Love Candle", "Happy Brownie", "Eternal Candle", "Holiday Drink",
    "Lush Bouquet", "Skull Flower", "Ion Gem", "Tama Gadget", "Artisan Brick",
    "Perfume Bottle", "Swag Bag", "Mini Oscar", "Genie Lamp", "Scared Cat",
    "Hex Pot", "Voodoo Doll", "Neko Helmet", "Snoop Dogg", "Sleigh Bell",
    "Snoop Cigar", "Spiced Wine", "Desk Calendar", "Lol Pop", "Light Sword",
    "Cookie Heart", "Lunar Snake", "Party Sparkler", "Crystal Ball", "Low Rider",
    "Clover Pin", "Bunny Muffin", "Faith Amulet", "Big Year", "Durov's Cap",
    "Plush Pepe", "Cupid Charm", "Gem Signet", "Heroic Helmet", "Fresh Socks",
    "Swiss Watch", "Valentine Box", "Spy Agaric", "Jolly Chimp", "Spring Basket",
    "Electric Skull", "Santa Hat", "Record Player", "Input Key", "Hypno Lollipop",
    "Snow Globe", "Stellar Rocket", "Evil Eye", "Sharp Tongue", "Winter Wreath",
    "Ionic Dryer", "Xmas Stocking", "Sakura Flower", "Love Potion", "Kissed Frog",
    "Snake Box", "Jingle Bells", "Astral Shard", "Top Hat", "Diamond Ring",
    "Magic Potion", "Whip Cupcake", "Mad Pumpkin", "Easter Egg", "Pet Snake",
    "Westside Sign", "Loot Bag", "Trapped Heart", "Ice Cream", "Berry Box",
    "Candy Cane", "Bonded Ring", "Vintage Cigar", "Heart Locket", "Jelly Bunny",
    "Jester Hat", "Precious Peach", "Instant Ramen", "Toy Bear", "Nail Bracelet",
    "Snow Mittens", "Eternal Rose", "Bow Tie", "Mousse Cake", "Sky Stilettos",
    "Signet Ring", "Homemade Cake"
];

// Reviews data with dates for sorting
const reviewsData = [
    // --- расширенная витрина отзывов ---
    { username: 'alik_shadow', gift: 'Jester Hat', text: 'продал Jester Hat тут, бот всё сам провёл. буду пользоваться ещё', date: '2026-06-16', rating: 5 },
    { username: 'raketa', gift: 'Top Hat', text: 'забрал Top Hat после оплаты, бот не отпустил пока не заплатил. топ', date: '2026-05-11', rating: 5 },
    { username: 'kotik', gift: 'Hex Pot', text: 'продал Hex Pot, норм но комса кусается немного', date: '2026-05-10', rating: 4 },
    { username: 'злодей_gift', gift: 'Perfume Bottle', text: 'гарант держал Perfume Bottle пока переводил деньги, потом отдал. надёжно', date: '2026-06-24', rating: 5 },
    { username: 'boba661', gift: 'Perfume Bottle', text: 'брал Perfume Bottle, в лс бы не рискнул, а тут бот держал сделку. спокойно', date: '2026-07-04', rating: 5 },
    { username: 'zaza', gift: 'Westside Sign', text: 'продавец кинул Westside Sign в гаранта, оплатил и сразу получил. быстро', date: '2026-06-24', rating: 5 },
    { username: 'zaza396', gift: 'Sharp Tongue', text: 'Sharp Tongue купил, всё честно, никто никого не наебал. рекомендую', date: '2026-06-07', rating: 5 },
    { username: 'морж_gift', gift: 'Evil Eye', text: 'Evil Eye купил, деньги шли долго, но в итоге всё ок', date: '2026-04-26', rating: 3 },
    { username: 'трактор_tg', gift: 'Durov\'s Cap', text: 'сделка на Durov\'s Cap прошла успешно, гарант отработал на все 100', date: '2026-03-21', rating: 5 },
    { username: 'yellow', gift: 'Flying Broom', text: 'покупал Flying Broom, деньги пришли не сразу но пришли. в целом норм', date: '2026-07-03', rating: 5 },
    { username: 'zaza40', gift: 'Flying Broom', text: 'купил Flying Broom, продавец закинул в бота и я спокойно оплатил. всё чисто', date: '2026-06-23', rating: 5 },
    { username: 'злодей', gift: 'Ion Gem', text: 'оплата за Ion Gem зависла, писал в поддержку пока решили', date: '2026-06-24', rating: 2 },
    { username: 'neo', gift: 'Snoop Dogg', text: 'продал Snoop Dogg, норм но комса кусается немного', date: '2026-03-21', rating: 4 },
    { username: 'злодей', gift: 'Toy Bear', text: 'покупал Toy Bear, деньги пришли не сразу но пришли. в целом норм', date: '2026-05-03', rating: 5 },
    { username: 'seller99381', gift: 'Scared Cat', text: 'сделка на Scared Cat прошла успешно, гарант отработал на все 100', date: '2026-06-21', rating: 5 },
    { username: 'romka162', gift: 'Love Potion', text: 'Love Potion купил, всё честно, никто никого не наебал. рекомендую', date: '2026-07-03', rating: 5 },
    { username: 'fenix', gift: 'Hanging Star', text: 'купил Hanging Star, продавец закинул в бота и я спокойно оплатил. всё чисто', date: '2026-05-19', rating: 5 },
    { username: 'sanya_p_vasya', gift: 'Astral Shard', text: 'escrow для телеги подарков реально работает, Astral Shard прошёл гладко', date: '2026-07-13', rating: 5 },
    { username: 'yellow', gift: 'Bonded Ring', text: 'сделка на Bonded Ring прошла успешно, гарант отработал на все 100', date: '2026-06-26', rating: 5 },
    { username: 'just_ok', gift: 'Nail Bracelet', text: 'забрал Nail Bracelet после оплаты, бот не отпустил пока не заплатил. топ', date: '2026-06-14', rating: 5 },
    { username: 'proger', gift: 'Neko Helmet', text: 'Neko Helmet купил, всё честно, никто никого не наебал. рекомендую', date: '2026-07-05', rating: 5 },
    { username: 'moon_kid', gift: 'Snow Globe', text: 'брал Snow Globe, в лс бы не рискнул, а тут бот держал сделку. спокойно', date: '2026-05-24', rating: 5 },
    { username: 'olegg', gift: 'Evil Eye', text: 'продавец кинул Evil Eye в гаранта, оплатил и сразу получил. быстро', date: '2026-06-06', rating: 5 },
    { username: 'kotik', gift: 'Skull Flower', text: 'купил Skull Flower, продавец закинул в бота и я спокойно оплатил. всё чисто', date: '2026-06-10', rating: 5, hasHeart: true },
    { username: 'shadow', gift: 'Nail Bracelet', text: 'Nail Bracelet забрал, всё нормально, но интерфейс мог быть попроще', date: '2026-02-08', rating: 4 },
    { username: 'sanya_p642', gift: 'Perfume Bottle', text: 'продал Perfume Bottle, норм но комса кусается немного', date: '2026-05-16', rating: 4 },
    { username: 'серый_x', gift: 'Low Rider', text: 'забрал Low Rider после оплаты, бот не отпустил пока не заплатил. топ', date: '2026-03-26', rating: 5 },
    { username: 'arty120', gift: 'Love Potion', text: 'продал Love Potion, норм но комса кусается немного', date: '2026-03-10', rating: 4 },
    { username: 'tradermax', gift: 'Heroic Helmet', text: 'брал Heroic Helmet, в лс бы не рискнул, а тут бот держал сделку. спокойно', date: '2026-06-13', rating: 5 },
    { username: 'gift_hunter', gift: 'Durov\'s Cap', text: 'Durov\'s Cap продал, покупатель забрал из бота и мне упали бабки. чётко', date: '2026-06-06', rating: 5 },
    { username: 'toxa', gift: 'Westside Sign', text: 'продал Westside Sign, было пару затыков но разрулили', date: '2026-06-07', rating: 3 },
    { username: 'donttrust_buyer_one', gift: 'Sharp Tongue', text: 'Sharp Tongue купил, деньги шли долго, но в итоге всё ок', date: '2026-05-13', rating: 3 },
    { username: 'nft_king156', gift: 'Bonded Ring', text: 'гарант держал Bonded Ring пока переводил деньги, потом отдал. надёжно', date: '2026-04-05', rating: 5, hasHeart: true },
    { username: 'dread', gift: 'Evil Eye', text: 'купил Evil Eye, гарант ок но минут 20 ждал пока продавец закинет', date: '2026-05-12', rating: 4 },
    { username: 'nft_king', gift: 'Voodoo Doll', text: 'забрал Voodoo Doll после оплаты, бот не отпустил пока не заплатил. топ', date: '2026-04-06', rating: 5 },
    { username: 'donttrust', gift: 'Toy Bear', text: 'сделка на Toy Bear прошла, но поддержка отвечала медленно', date: '2026-07-15', rating: 3 },
    { username: 'daniil641', gift: 'Sky Stilettos', text: 'Sky Stilettos продал, покупатель забрал из бота и мне упали бабки. чётко', date: '2026-01-20', rating: 5 },
    { username: 'kirscht', gift: 'Nail Bracelet', text: 'брал Nail Bracelet, гарант отработал, только ждать пришлось подольше', date: '2026-06-11', rating: 4 },
    { username: 'sigma_boy', gift: 'Vintage Cigar', text: 'брал Vintage Cigar, гарант отработал, только ждать пришлось подольше', date: '2026-04-06', rating: 4 },
    { username: 'волк', gift: 'Neko Helmet', text: 'брал Neko Helmet, гарант отработал, только ждать пришлось подольше', date: '2026-01-01', rating: 4 },
    { username: 'just_ok', gift: 'Sleigh Bell', text: 'deal on Sleigh Bell went well, money arrived without issues', date: '2026-06-04', rating: 5 },
    { username: 'dread668', gift: 'Snow Globe', text: 'продавец кинул Snow Globe в гаранта, оплатил и сразу получил. быстро', date: '2026-05-12', rating: 5 },
    { username: 'glebrus', gift: 'Mini Oscar', text: 'sold Mini Oscar via the bot, escrow held funds until paid. smooth', date: '2026-01-26', rating: 5 },
    { username: 'cryptoboy', gift: 'Toy Bear', text: 'продал Toy Bear тут, бот всё сам провёл. буду пользоваться ещё', date: '2026-02-03', rating: 5 },
    { username: 'босс', gift: 'Magic Potion', text: 'брал Magic Potion, гарант отработал, только ждать пришлось подольше', date: '2026-03-21', rating: 4 },
    { username: 'boba_grimm', gift: 'Voodoo Doll', text: 'сделка на Voodoo Doll прошла успешно, гарант отработал на все 100', date: '2026-07-10', rating: 5 },
    { username: 'cryptoboy', gift: 'Signet Ring', text: 'купил Signet Ring, гарант ок но минут 20 ждал пока продавец закинет', date: '2026-07-15', rating: 4 },
    { username: 'denchik', gift: 'Santa Hat', text: 'Santa Hat продал, покупатель забрал из бота и мне упали бабки. чётко', date: '2026-07-13', rating: 5 },
    { username: 'boba', gift: 'Berry Box', text: 'гарант держал Berry Box пока переводил деньги, потом отдал. надёжно', date: '2026-05-05', rating: 5 },
    { username: 'pavel_v_proger', gift: 'Ginger Cookie', text: 'гарант держал Ginger Cookie пока переводил деньги, потом отдал. надёжно', date: '2026-07-02', rating: 5 },
    { username: 'just_ok', gift: 'Jack-in-the-Box', text: 'sold Jack-in-the-Box via the bot, escrow held funds until paid. smooth', date: '2026-07-11', rating: 5 },
    { username: 'zloy', gift: 'Toy Bear', text: 'Toy Bear купил, всё честно, никто никого не наебал. рекомендую', date: '2026-05-06', rating: 5 },
    { username: 'морж', gift: 'Westside Sign', text: 'escrow для телеги подарков реально работает, Westside Sign прошёл гладко', date: '2026-04-24', rating: 5 },
    { username: 'лютый_2', gift: 'Spy Agaric', text: 'deal on Spy Agaric went well, money arrived without issues', date: '2026-01-12', rating: 5 },
    { username: 'gift_hunter60', gift: 'Love Potion', text: 'продал Love Potion, норм но комса кусается немного', date: '2026-06-01', rating: 4 },
    { username: 'biba_yellow', gift: 'Spy Agaric', text: 'продал Spy Agaric через бота, гарант держал пока платили. деньги пришли без косяков', date: '2026-03-11', rating: 5 },
    { username: 'nft_king770', gift: 'Sky Stilettos', text: 'продал Sky Stilettos через бота, гарант держал пока платили. деньги пришли без косяков', date: '2026-07-05', rating: 5 },
    { username: 'tradermax746', gift: 'Flying Broom', text: 'сделка на Flying Broom прошла успешно, гарант отработал на все 100', date: '2026-07-01', rating: 5 },
    { username: 'grimm_toxa', gift: 'Heroic Helmet', text: 'брал Heroic Helmet, гарант отработал, только ждать пришлось подольше', date: '2026-06-13', rating: 4 },
    { username: 'stasik842', gift: 'Scared Cat', text: 'Scared Cat продал, покупатель забрал из бота и мне упали бабки. чётко', date: '2026-02-07', rating: 5 },
    { username: 'dread', gift: 'Bow Tie', text: 'продал Bow Tie, было пару затыков но разрулили', date: '2026-01-19', rating: 3 },
    { username: 'donttrust', gift: 'Genie Lamp', text: 'Genie Lamp купил, всё честно, никто никого не наебал. рекомендую', date: '2026-06-16', rating: 5 },
    { username: 'donttrust152', gift: 'Restless Jar', text: 'продал Restless Jar тут, бот всё сам провёл. буду пользоваться ещё', date: '2026-07-10', rating: 5 },
    { username: 'xdmen', gift: 'Signet Ring', text: 'продал Signet Ring, было пару затыков но разрулили', date: '2026-06-05', rating: 3 },
    { username: 'pavel_v', gift: 'Toy Bear', text: 'bought Toy Bear, seller dropped it in the bot and i paid safely', date: '2026-05-17', rating: 5 },
    { username: 'краш', gift: 'Nail Bracelet', text: 'sold Nail Bracelet via the bot, escrow held funds until paid. smooth', date: '2026-05-13', rating: 5, hasHeart: true },
    { username: 'дампер', gift: 'Toy Bear', text: 'продал Toy Bear тут, бот всё сам провёл. буду пользоваться ещё', date: '2026-04-09', rating: 5 },
    { username: 'vasya', gift: 'Sky Stilettos', text: 'продал Sky Stilettos, было пару затыков но разрулили', date: '2026-01-26', rating: 3 },
    { username: 'zaza_proger', gift: 'Electric Skull', text: 'продал Electric Skull, норм но комса кусается немного', date: '2026-07-11', rating: 4 },
    { username: 'nft_king_olegg', gift: 'Crystal Ball', text: 'escrow для телеги подарков реально работает, Crystal Ball прошёл гладко', date: '2026-06-26', rating: 5 },
    { username: 'дядя', gift: 'Sky Stilettos', text: 'Sky Stilettos продал, покупатель забрал из бота и мне упали бабки. чётко', date: '2026-05-24', rating: 5 },
    { username: 'tg_gifts_shadow', gift: 'Jelly Bunny', text: 'deal on Jelly Bunny went well, money arrived without issues', date: '2026-06-14', rating: 5 },
    { username: 'kotik322', gift: 'Nail Bracelet', text: 'продавец кинул Nail Bracelet в гаранта, оплатил и сразу получил. быстро', date: '2026-07-15', rating: 5 },
    { username: 'гоша_2', gift: 'Mini Oscar', text: 'продал Mini Oscar через бота, гарант держал пока платили. деньги пришли без косяков', date: '2026-02-13', rating: 5 },
    { username: 'arty314', gift: 'Love Potion', text: 'забрал Love Potion после оплаты, бот не отпустил пока не заплатил. топ', date: '2026-05-04', rating: 5 },
    { username: 'мираж', gift: 'Skull Flower', text: 'гарант держал Skull Flower пока переводил деньги, потом отдал. надёжно', date: '2026-06-18', rating: 5 },
    { username: 'buyer_one66', gift: 'Westside Sign', text: 'брал Westside Sign, в лс бы не рискнул, а тут бот держал сделку. спокойно', date: '2026-06-15', rating: 5 },
    { username: 'glebrus660', gift: 'Skull Flower', text: 'Skull Flower продал, покупатель забрал из бота и мне упали бабки. чётко', date: '2026-02-20', rating: 5 },
    { username: 'vasya152', gift: 'Loot Bag', text: 'купил Loot Bag, продавец закинул в бота и я спокойно оплатил. всё чисто', date: '2026-06-02', rating: 5 },
    { username: 'pepe_lord_zloy', gift: 'Durov\'s Cap', text: 'сделка на Durov\'s Cap прошла, но поддержка отвечала медленно', date: '2026-04-17', rating: 3 },
    { username: 'дампер', gift: 'Snow Globe', text: 'Snow Globe — сделка тормозила, в итоге разрулили но осадок остался', date: '2026-05-22', rating: 1 },
    { username: 'frozt', gift: 'Plush Pepe', text: 'брал Plush Pepe, гарант отработал, только ждать пришлось подольше', date: '2026-06-01', rating: 4 },
    { username: 'царь', gift: 'Jester Hat', text: 'продал Jester Hat через бота, гарант держал пока платили. деньги пришли без косяков', date: '2026-06-19', rating: 5 },
    { username: 'nft_king908', gift: 'Homemade Cake', text: 'escrow для телеги подарков реально работает, Homemade Cake прошёл гладко', date: '2026-05-12', rating: 5 },
    { username: 'vasya396', gift: 'Star Notepad', text: 'Star Notepad продал, покупатель забрал из бота и мне упали бабки. чётко', date: '2026-05-15', rating: 5 },
    { username: 'гоша', gift: 'Vintage Cigar', text: 'got Vintage Cigar after payment, guarantor worked fine. recommend', date: '2026-07-01', rating: 5, hasHeart: true },
    { username: 'nikitos205', gift: 'Santa Hat', text: 'купил Santa Hat, продавец закинул в бота и я спокойно оплатил. всё чисто', date: '2026-03-16', rating: 5 },
    { username: 'дядя_2', gift: 'Bunny Muffin', text: 'брал Bunny Muffin, в лс бы не рискнул, а тут бот держал сделку. спокойно', date: '2026-03-23', rating: 5 },
    { username: 'misha', gift: 'Cookie Heart', text: 'сделка на Cookie Heart прошла, чуть подтупливал бот но деньги дошли', date: '2026-03-20', rating: 4 },
    { username: 'dread_nikitos', gift: 'Magic Potion', text: 'продал Magic Potion тут, бот всё сам провёл. буду пользоваться ещё', date: '2026-03-25', rating: 5, hasHeart: true },
    { username: 'печенька', gift: 'Love Potion', text: 'продавец кинул Love Potion в гаранта, оплатил и сразу получил. быстро', date: '2026-05-02', rating: 5 },
    { username: 'мираж', gift: 'Perfume Bottle', text: 'купил Perfume Bottle, гарант ок но минут 20 ждал пока продавец закинет', date: '2026-06-12', rating: 4 },
    { username: 'гоша_2', gift: 'Loot Bag', text: 'deal on Loot Bag went well, money arrived without issues', date: '2026-02-03', rating: 5 },
    { username: 'lolz_fan_tradermax', gift: 'Input Key', text: 'deal on Input Key went well, money arrived without issues', date: '2026-03-07', rating: 5 },
    { username: 'морж', gift: 'Eternal Rose', text: 'брал Eternal Rose, в лс бы не рискнул, а тут бот держал сделку. спокойно', date: '2026-05-05', rating: 5 },
    { username: 'arty171', gift: 'Mini Oscar', text: 'got Mini Oscar after payment, guarantor worked fine. recommend', date: '2026-07-07', rating: 4 },
    { username: 'lolz_fan412', gift: 'Love Potion', text: 'забрал Love Potion после оплаты, бот не отпустил пока не заплатил. топ', date: '2026-05-01', rating: 5 },
    { username: 'kirscht', gift: 'Kissed Frog', text: 'Kissed Frog продал, покупатель забрал из бота и мне упали бабки. чётко', date: '2026-06-07', rating: 5 },
    { username: 'zloy', gift: 'Bunny Muffin', text: 'оплата за Bunny Muffin зависла, писал в поддержку пока решили', date: '2026-06-24', rating: 2 },
    { username: 'seller99840', gift: 'Skull Flower', text: 'забрал Skull Flower после оплаты, бот не отпустил пока не заплатил. топ', date: '2026-05-16', rating: 5 },
    { username: 'mrx', gift: 'Perfume Bottle', text: 'купил Perfume Bottle, продавец закинул в бота и я спокойно оплатил. всё чисто', date: '2026-04-24', rating: 5 },
    { username: 'seller99', gift: 'Heroic Helmet', text: 'Heroic Helmet брал, долго висела сделка, нервов потрепало', date: '2026-06-15', rating: 2 },
    { username: 'печенька', gift: 'Snoop Dogg', text: 'брал Snoop Dogg, в лс бы не рискнул, а тут бот держал сделку. спокойно', date: '2026-01-12', rating: 5 },
    { username: 'boba', gift: 'Gem Signet', text: 'брал Gem Signet, в лс бы не рискнул, а тут бот держал сделку. спокойно', date: '2026-04-09', rating: 5 },
    { username: 'neo', gift: 'Voodoo Doll', text: 'продавец кинул Voodoo Doll в гаранта, оплатил и сразу получил. быстро', date: '2026-02-03', rating: 5 },
    { username: 'коляныч', gift: 'Love Potion', text: 'продавец кинул Love Potion в гаранта, оплатил и сразу получил. быстро', date: '2026-06-18', rating: 5 },
    { username: 'gift_hunter', gift: 'Mad Pumpkin', text: 'продал Mad Pumpkin, норм но комса кусается немного', date: '2026-05-25', rating: 4 },
    { username: 'коляныч_gift', gift: 'Love Potion', text: 'купил Love Potion, продавец закинул в бота и я спокойно оплатил. всё чисто', date: '2026-05-26', rating: 5 },
    { username: 'romka', gift: 'Nail Bracelet', text: 'bought Nail Bracelet, seller dropped it in the bot and i paid safely', date: '2026-06-06', rating: 4 },
    { username: 'just_ok', gift: 'Vintage Cigar', text: 'гарант держал Vintage Cigar пока переводил деньги, потом отдал. надёжно', date: '2026-05-28', rating: 5 },
    { username: 'moon_kid', gift: 'Witch Hat', text: 'брал Witch Hat, гарант отработал, только ждать пришлось подольше', date: '2026-05-13', rating: 4 },
    { username: 'romka', gift: 'Gem Signet', text: 'сделка на Gem Signet прошла успешно, гарант отработал на все 100', date: '2026-06-10', rating: 5 },
    { username: 'pavel_v', gift: 'Homemade Cake', text: 'покупал Homemade Cake, деньги пришли не сразу но пришли. в целом норм', date: '2026-06-28', rating: 5 },
    { username: 'hodl', gift: 'Flying Broom', text: 'купил Flying Broom, гарант ок но минут 20 ждал пока продавец закинет', date: '2026-05-04', rating: 4 },
    { username: 'трактор', gift: 'Bonded Ring', text: 'escrow для телеги подарков реально работает, Bonded Ring прошёл гладко', date: '2026-07-06', rating: 5 },
    { username: 'nikitos_tg_gifts', gift: 'Vintage Cigar', text: 'сделка на Vintage Cigar прошла, чуть подтупливал бот но деньги дошли', date: '2026-07-07', rating: 4 },
    { username: 'коляныч', gift: 'Toy Bear', text: 'гарант держал Toy Bear пока переводил деньги, потом отдал. надёжно', date: '2026-07-15', rating: 5 },
    { username: 'cryptoboy314', gift: 'Mad Pumpkin', text: 'купил Mad Pumpkin, гарант ок но минут 20 ждал пока продавец закинет', date: '2026-01-17', rating: 4 },
    { username: 'hodl_zloy', gift: 'Gem Signet', text: 'покупал Gem Signet, деньги пришли не сразу но пришли. в целом норм', date: '2026-06-14', rating: 5 },
    { username: 'злодей_x', gift: 'Vintage Cigar', text: 'гарант держал Vintage Cigar пока переводил деньги, потом отдал. надёжно', date: '2026-07-12', rating: 5 },
    { username: 'glebrus718', gift: 'Trapped Heart', text: 'сделка на Trapped Heart прошла, но поддержка отвечала медленно', date: '2026-03-10', rating: 3 },
    { username: 'proger_stasik', gift: 'Input Key', text: 'Input Key забрал, всё нормально, но интерфейс мог быть попроще', date: '2026-04-11', rating: 4 },
    { username: 'tg_gifts', gift: 'Eternal Rose', text: 'покупал Eternal Rose, деньги пришли не сразу но пришли. в целом норм', date: '2026-04-10', rating: 5 },
    { username: 'gift_hunter', gift: 'Astral Shard', text: 'deal on Astral Shard went well, money arrived without issues', date: '2026-05-12', rating: 4 },
    { username: 'donttrust_pepe_lord', gift: 'Magic Potion', text: 'Magic Potion купил, всё честно, никто никого не наебал. рекомендую', date: '2026-01-07', rating: 5 },
    { username: 'seller99933', gift: 'Electric Skull', text: 'брал Electric Skull, в лс бы не рискнул, а тут бот держал сделку. спокойно', date: '2026-05-27', rating: 5 },
    { username: 'печенька_2', gift: 'Ginger Cookie', text: 'Ginger Cookie продал, покупатель забрал из бота и мне упали бабки. чётко', date: '2026-06-22', rating: 5 },
    { username: 'sigma_boy_pavel_v', gift: 'Scared Cat', text: 'брал Scared Cat, гарант отработал, только ждать пришлось подольше', date: '2026-05-17', rating: 4 },
    { username: 'гоша', gift: 'Hanging Star', text: 'оплата за Hanging Star зависла, писал в поддержку пока решили', date: '2026-04-28', rating: 2 },
    { username: 'buyer_one289', gift: 'Cookie Heart', text: 'Cookie Heart продал, покупатель забрал из бота и мне упали бабки. чётко', date: '2026-06-09', rating: 5 },
    { username: 'босс', gift: 'Heroic Helmet', text: 'сделка на Heroic Helmet прошла успешно, гарант отработал на все 100', date: '2026-07-10', rating: 5 },
    { username: 'дядя', gift: 'Restless Jar', text: 'продавец кинул Restless Jar в гаранта, оплатил и сразу получил. быстро', date: '2026-05-04', rating: 5 },
    { username: 'nikitos568', gift: 'Input Key', text: 'продал Input Key тут, бот всё сам провёл. буду пользоваться ещё', date: '2026-05-02', rating: 5 },
    { username: 'toxa', gift: 'Bunny Muffin', text: 'продал Bunny Muffin через бота, гарант держал пока платили. деньги пришли без косяков', date: '2026-06-19', rating: 5 },
    { username: 'волк', gift: 'Neko Helmet', text: 'Neko Helmet забрал, всё нормально, но интерфейс мог быть попроще', date: '2026-03-17', rating: 4 },
    { username: 'buyer_one', gift: 'Cookie Heart', text: 'сделка на Cookie Heart прошла успешно, гарант отработал на все 100', date: '2026-06-14', rating: 5 },
    { username: 'proger', gift: 'Bonded Ring', text: 'продал Bonded Ring тут, бот всё сам провёл. буду пользоваться ещё', date: '2026-06-19', rating: 5 },
    { username: 'proger', gift: 'Party Sparkler', text: 'deal on Party Sparkler went well, money arrived without issues', date: '2026-06-02', rating: 5, hasHeart: true },
    { username: 'mrx', gift: 'Swiss Watch', text: 'забрал Swiss Watch после оплаты, бот не отпустил пока не заплатил. топ', date: '2026-04-05', rating: 5 },
    { username: 'sigma_boy', gift: 'Electric Skull', text: 'купил Electric Skull, гарант ок но минут 20 ждал пока продавец закинет', date: '2026-05-20', rating: 4 },
    { username: 'moon_kid_pavel_v', gift: 'Bunny Muffin', text: 'покупал Bunny Muffin, деньги пришли не сразу но пришли. в целом норм', date: '2026-03-26', rating: 5 },
    { username: 'gift_hunter141', gift: 'Sharp Tongue', text: 'покупал Sharp Tongue, деньги пришли не сразу но пришли. в целом норм', date: '2026-04-20', rating: 5 },
    { username: 'maks_tg', gift: 'Heroic Helmet', text: 'гарант держал Heroic Helmet пока переводил деньги, потом отдал. надёжно', date: '2026-06-22', rating: 5 },
    { username: 'serega', gift: 'Snoop Dogg', text: 'Snoop Dogg забрал, всё нормально, но интерфейс мог быть попроще', date: '2026-05-21', rating: 4 },
    { username: 'boba', gift: 'Berry Box', text: 'Berry Box — сделка тормозила, в итоге разрулили но осадок остался', date: '2026-03-05', rating: 1 },
    { username: 'sigma_boy', gift: 'Genie Lamp', text: 'Genie Lamp купил, всё честно, никто никого не наебал. рекомендую', date: '2026-06-19', rating: 5 },
    { username: 'denchik', gift: 'Vintage Cigar', text: 'сделка на Vintage Cigar прошла, но поддержка отвечала медленно', date: '2026-06-19', rating: 3 },
    { username: 'mrx767', gift: 'Jack-in-the-Box', text: 'Jack-in-the-Box брал, долго висела сделка, нервов потрепало', date: '2026-03-28', rating: 2 },
    { username: 'moon_kid239', gift: 'Perfume Bottle', text: 'брал Perfume Bottle, гарант отработал, только ждать пришлось подольше', date: '2026-07-06', rating: 4 },
    { username: 'hodl502', gift: 'Gem Signet', text: 'Gem Signet забрал, всё нормально, но интерфейс мог быть попроще', date: '2026-05-08', rating: 4 },
    { username: 'печенька', gift: 'Neko Helmet', text: 'Neko Helmet продал, покупатель забрал из бота и мне упали бабки. чётко', date: '2026-02-14', rating: 5 },
    { username: 'царь_x', gift: 'Snoop Dogg', text: 'гарант держал Snoop Dogg пока переводил деньги, потом отдал. надёжно', date: '2026-06-18', rating: 5 },
    { username: 'xdmen626', gift: 'Nail Bracelet', text: 'сделка на Nail Bracelet прошла, но поддержка отвечала медленно', date: '2026-01-21', rating: 3 },
    { username: 'zloy_shadow', gift: 'Plush Pepe', text: 'брал Plush Pepe, в лс бы не рискнул, а тут бот держал сделку. спокойно', date: '2026-04-08', rating: 5 },
    { username: 'vitaliy_raketa', gift: 'Heroic Helmet', text: 'сделка на Heroic Helmet прошла, чуть подтупливал бот но деньги дошли', date: '2026-04-27', rating: 4 },
    { username: 'nft_king846', gift: 'Sleigh Bell', text: 'покупал Sleigh Bell, деньги пришли не сразу но пришли. в целом норм', date: '2026-05-04', rating: 5 },
    { username: 'трактор', gift: 'Love Potion', text: 'Love Potion забрал, всё нормально, но интерфейс мог быть попроще', date: '2026-04-14', rating: 4 },
    { username: 'yellow', gift: 'Precious Peach', text: 'got Precious Peach after payment, guarantor worked fine. recommend', date: '2026-07-05', rating: 5 },
    { username: 'гоша', gift: 'Jack-in-the-Box', text: 'продал Jack-in-the-Box тут, бот всё сам провёл. буду пользоваться ещё', date: '2026-02-02', rating: 5 },
    { username: 'артём', gift: 'Lush Bouquet', text: 'продавец кинул Lush Bouquet в гаранта, оплатил и сразу получил. быстро', date: '2026-05-11', rating: 5 },
    { username: 'sanya_p', gift: 'Trapped Heart', text: 'Trapped Heart продал, покупатель забрал из бота и мне упали бабки. чётко', date: '2026-05-15', rating: 5 },
    { username: 'мираж', gift: 'Hanging Star', text: 'купил Hanging Star, гарант ок но минут 20 ждал пока продавец закинет', date: '2026-07-11', rating: 4 },
    { username: 'артём_x', gift: 'Skull Flower', text: 'сделка на Skull Flower прошла, но поддержка отвечала медленно', date: '2026-05-03', rating: 3 },
    { username: 'pavel_v_apex', gift: 'Hex Pot', text: 'продал Hex Pot тут, бот всё сам провёл. буду пользоваться ещё', date: '2026-06-22', rating: 5, hasHeart: true },
    { username: 'царь', gift: 'Mighty Arm', text: 'брал Mighty Arm, в лс бы не рискнул, а тут бот держал сделку. спокойно', date: '2026-01-12', rating: 5 },
    { username: 'xdmen_sigma_boy', gift: 'Loot Bag', text: 'Loot Bag купил, всё честно, никто никого не наебал. рекомендую', date: '2026-05-16', rating: 5 },
    { username: 'батя_x', gift: 'Diamond Ring', text: 'продавец кинул Diamond Ring в гаранта, оплатил и сразу получил. быстро', date: '2026-05-03', rating: 5 },
    { username: 'donttrust', gift: 'Mad Pumpkin', text: 'продавец кинул Mad Pumpkin в гаранта, оплатил и сразу получил. быстро', date: '2026-02-08', rating: 5 },
    { username: 'xdmen288', gift: 'Sleigh Bell', text: 'продал Sleigh Bell тут, бот всё сам провёл. буду пользоваться ещё', date: '2026-06-09', rating: 5 },
    { username: 'buyer_one', gift: 'Swiss Watch', text: 'продал Swiss Watch, норм но комса кусается немного', date: '2026-04-11', rating: 4 },
    { username: 'tg_gifts', gift: 'Durov\'s Cap', text: 'сделка на Durov\'s Cap прошла, чуть подтупливал бот но деньги дошли', date: '2026-03-02', rating: 4 },
    { username: 'gift_hunter', gift: 'Snow Globe', text: 'купил Snow Globe, продавец закинул в бота и я спокойно оплатил. всё чисто', date: '2026-07-14', rating: 5 },
    { username: 'neo_moon_kid', gift: 'Snow Globe', text: 'Snow Globe продал, покупатель забрал из бота и мне упали бабки. чётко', date: '2026-04-21', rating: 5 },
    { username: 'olegg_denchik', gift: 'Toy Bear', text: 'гарант держал Toy Bear пока переводил деньги, потом отдал. надёжно', date: '2026-06-20', rating: 5 },
    { username: 'hodl171', gift: 'Homemade Cake', text: 'deal on Homemade Cake went well, money arrived without issues', date: '2026-04-27', rating: 5, hasHeart: true },
    { username: 'zloy', gift: 'Neko Helmet', text: 'сделка на Neko Helmet прошла успешно, гарант отработал на все 100', date: '2026-06-06', rating: 5 },
    { username: 'коляныч', gift: 'Party Sparkler', text: 'брал Party Sparkler, в лс бы не рискнул, а тут бот держал сделку. спокойно', date: '2026-05-09', rating: 5 },
    { username: 'denchik', gift: 'Bonded Ring', text: 'escrow для телеги подарков реально работает, Bonded Ring прошёл гладко', date: '2026-04-17', rating: 5 },
    { username: 'frozt', gift: 'Crystal Ball', text: 'Crystal Ball купил, всё честно, никто никого не наебал. рекомендую', date: '2026-01-11', rating: 5 },
    { username: 'gift_hunter', gift: 'Bow Tie', text: 'sold Bow Tie via the bot, escrow held funds until paid. smooth', date: '2026-04-06', rating: 5 },
    { username: 'misha', gift: 'Lush Bouquet', text: 'гарант держал Lush Bouquet пока переводил деньги, потом отдал. надёжно', date: '2026-06-13', rating: 5 },
    { username: 'pepe_lord725', gift: 'Skull Flower', text: 'сделка на Skull Flower прошла, но поддержка отвечала медленно', date: '2026-07-14', rating: 3 },
    { username: 'nft_king', gift: 'Kissed Frog', text: 'sold Kissed Frog via the bot, escrow held funds until paid. smooth', date: '2026-06-10', rating: 4 },
    { username: 'yellow', gift: 'Bow Tie', text: 'got Bow Tie after payment, guarantor worked fine. recommend', date: '2026-05-02', rating: 5 },
    { username: 'sanya_p_buyer_one', gift: 'Jelly Bunny', text: 'купил Jelly Bunny, гарант ок но минут 20 ждал пока продавец закинет', date: '2026-01-21', rating: 4 },
    { username: 'seller99', gift: 'Spy Agaric', text: 'гарант держал Spy Agaric пока переводил деньги, потом отдал. надёжно', date: '2026-05-03', rating: 5 },
    { username: 'dread', gift: 'Crystal Ball', text: 'продал Crystal Ball тут, бот всё сам провёл. буду пользоваться ещё', date: '2026-06-18', rating: 5 },
    { username: 'proger483', gift: 'Diamond Ring', text: 'deal on Diamond Ring went well, money arrived without issues', date: '2026-06-28', rating: 4 },
    { username: 'toxa122', gift: 'Ginger Cookie', text: 'купил Ginger Cookie, гарант ок но минут 20 ждал пока продавец закинет', date: '2026-06-01', rating: 4 },
    { username: 'glebrus', gift: 'Berry Box', text: 'сделка на Berry Box прошла успешно, гарант отработал на все 100', date: '2026-05-12', rating: 5 },
    { username: 'tg_gifts_lolz_fan', gift: 'Flying Broom', text: 'продал Flying Broom через бота, гарант держал пока платили. деньги пришли без косяков', date: '2026-07-14', rating: 5 },
    { username: 'волк', gift: 'Sharp Tongue', text: 'Sharp Tongue продал, покупатель забрал из бота и мне упали бабки. чётко', date: '2026-02-14', rating: 5 },
    { username: 'гоша_tg', gift: 'Restless Jar', text: 'Restless Jar — сделка тормозила, в итоге разрулили но осадок остался', date: '2026-04-09', rating: 1 },
    { username: 'sanya_p', gift: 'Voodoo Doll', text: 'Voodoo Doll купил, всё честно, никто никого не наебал. рекомендую', date: '2026-01-10', rating: 5, hasHeart: true },
    { username: 'proger632', gift: 'Party Sparkler', text: 'сделка на Party Sparkler прошла, чуть подтупливал бот но деньги дошли', date: '2026-02-09', rating: 4 },
    { username: 'sigma_boy', gift: 'Kissed Frog', text: 'Kissed Frog купил, деньги шли долго, но в итоге всё ок', date: '2026-05-20', rating: 3 },
    { username: 'daniil', gift: 'Electric Skull', text: 'продал Electric Skull, норм но комса кусается немного', date: '2026-06-28', rating: 4 },
    { username: 'zaza676', gift: 'Spy Agaric', text: 'купил Spy Agaric, гарант ок но минут 20 ждал пока продавец закинет', date: '2026-07-05', rating: 4 },
    { username: 'gift_hunter', gift: 'Electric Skull', text: 'sold Electric Skull via the bot, escrow held funds until paid. smooth', date: '2026-07-08', rating: 5 },
    { username: 'biba_cryptoboy', gift: 'Flying Broom', text: 'брал Flying Broom, гарант отработал, только ждать пришлось подольше', date: '2026-01-28', rating: 4 },
    { username: 'vasya385', gift: 'Perfume Bottle', text: 'sold Perfume Bottle via the bot, escrow held funds until paid. smooth', date: '2026-06-01', rating: 5 },
    { username: 'fenix', gift: 'Swiss Watch', text: 'bought Swiss Watch, seller dropped it in the bot and i paid safely', date: '2026-06-24', rating: 5 },
    { username: 'добрый', gift: 'Restless Jar', text: 'оплата за Restless Jar зависла, писал в поддержку пока решили', date: '2026-06-14', rating: 2 },
    { username: 'fenix', gift: 'Santa Hat', text: 'Santa Hat купил, деньги шли долго, но в итоге всё ок', date: '2026-06-10', rating: 3 },
    { username: 'proger814', gift: 'Mad Pumpkin', text: 'продал Mad Pumpkin тут, бот всё сам провёл. буду пользоваться ещё', date: '2026-06-06', rating: 5 },
    { username: 'arty39', gift: 'Crystal Ball', text: 'Crystal Ball купил, деньги шли долго, но в итоге всё ок', date: '2026-02-26', rating: 3 },
    { username: 'гоша', gift: 'Input Key', text: 'брал Input Key, в лс бы не рискнул, а тут бот держал сделку. спокойно', date: '2026-04-15', rating: 5 },
    { username: 'pavel_v', gift: 'Ion Gem', text: 'покупал Ion Gem, деньги пришли не сразу но пришли. в целом норм', date: '2026-02-07', rating: 5 },
    { username: 'arty', gift: 'Toy Bear', text: 'сделка на Toy Bear прошла, чуть подтупливал бот но деньги дошли', date: '2026-06-09', rating: 4 },
    { username: 'denchik', gift: 'Magic Potion', text: 'продал Magic Potion тут, бот всё сам провёл. буду пользоваться ещё', date: '2026-01-14', rating: 5 },
    { username: 'dread711', gift: 'Record Player', text: 'покупал Record Player, деньги пришли не сразу но пришли. в целом норм', date: '2026-06-11', rating: 5 },
    { username: 'boba262', gift: 'Top Hat', text: 'покупал Top Hat, деньги пришли не сразу но пришли. в целом норм', date: '2026-05-10', rating: 5 },
    { username: 'seller99539', gift: 'Mad Pumpkin', text: 'купил Mad Pumpkin, продавец закинул в бота и я спокойно оплатил. всё чисто', date: '2026-01-11', rating: 5, hasHeart: true },
    { username: 'гоша', gift: 'Perfume Bottle', text: 'гарант держал Perfume Bottle пока переводил деньги, потом отдал. надёжно', date: '2026-02-27', rating: 5 },
    { username: 'fenix', gift: 'Input Key', text: 'Input Key забрал, всё нормально, но интерфейс мог быть попроще', date: '2026-05-24', rating: 4 },
    { username: 'lolz_fan319', gift: 'Jelly Bunny', text: 'купил Jelly Bunny, гарант ок но минут 20 ждал пока продавец закинет', date: '2026-01-06', rating: 4 },
    { username: 'tradermax', gift: 'Toy Bear', text: 'брал Toy Bear, в лс бы не рискнул, а тут бот держал сделку. спокойно', date: '2026-02-01', rating: 5 },
    { username: 'just_ok_daniil', gift: 'Trapped Heart', text: 'Trapped Heart брал, долго висела сделка, нервов потрепало', date: '2026-04-14', rating: 2 },
    { username: 'vasya439', gift: 'Toy Bear', text: 'deal on Toy Bear went well, money arrived without issues', date: '2026-06-16', rating: 4 },
    { username: 'lolz_fan142', gift: 'Bunny Muffin', text: 'сделка на Bunny Muffin прошла, чуть подтупливал бот но деньги дошли', date: '2026-07-05', rating: 4 },
    { username: 'sigma_boy467', gift: 'Plush Pepe', text: 'Plush Pepe купил, деньги шли долго, но в итоге всё ок', date: '2026-06-05', rating: 3 },
    { username: 'denchik744', gift: 'Skull Flower', text: 'escrow для телеги подарков реально работает, Skull Flower прошёл гладко', date: '2026-07-07', rating: 5 },
    { username: 'boba', gift: 'Signet Ring', text: 'забрал Signet Ring после оплаты, бот не отпустил пока не заплатил. топ', date: '2026-07-04', rating: 5 },
    { username: 'mrx', gift: 'Durov\'s Cap', text: 'сделка на Durov\'s Cap прошла успешно, гарант отработал на все 100', date: '2026-05-21', rating: 5, hasHeart: true },
    { username: 'proger879', gift: 'Star Notepad', text: 'гарант держал Star Notepad пока переводил деньги, потом отдал. надёжно', date: '2026-03-22', rating: 5 },
    { username: 'cryptoboy562', gift: 'Plush Pepe', text: 'escrow для телеги подарков реально работает, Plush Pepe прошёл гладко', date: '2026-02-20', rating: 5 },
    { username: 'сынбога', gift: 'Hanging Star', text: 'Hanging Star продал, покупатель забрал из бота и мне упали бабки. чётко', date: '2026-05-27', rating: 5 },
    { username: 'daniil', gift: 'Jester Hat', text: 'брал Jester Hat, гарант отработал, только ждать пришлось подольше', date: '2026-01-14', rating: 4 },
    { username: 'cryptoboy832', gift: 'Flying Broom', text: 'Flying Broom забрал, всё нормально, но интерфейс мог быть попроще', date: '2026-06-13', rating: 4 },
    { username: 'toxa', gift: 'Bunny Muffin', text: 'продал Bunny Muffin тут, бот всё сам провёл. буду пользоваться ещё', date: '2026-05-02', rating: 5 },
    { username: 'дядя', gift: 'Heroic Helmet', text: 'Heroic Helmet брал, долго висела сделка, нервов потрепало', date: '2026-03-03', rating: 2 },
    { username: 'nikitos', gift: 'Signet Ring', text: 'продал Signet Ring тут, бот всё сам провёл. буду пользоваться ещё', date: '2026-06-19', rating: 5 },
    { username: 'батя_2', gift: 'Ion Gem', text: 'продавец кинул Ion Gem в гаранта, оплатил и сразу получил. быстро', date: '2026-07-09', rating: 5 },
    { username: 'dread', gift: 'Durov\'s Cap', text: 'escrow для телеги подарков реально работает, Durov\'s Cap прошёл гладко', date: '2026-01-07', rating: 5 },
    { username: 'glebrus_serega', gift: 'Skull Flower', text: 'продал Skull Flower, было пару затыков но разрулили', date: '2026-02-02', rating: 3 },
    { username: 'misha599', gift: 'Skull Flower', text: 'Skull Flower продал, покупатель забрал из бота и мне упали бабки. чётко', date: '2026-07-06', rating: 5 },
    { username: 'grimm698', gift: 'Plush Pepe', text: 'сделка на Plush Pepe прошла успешно, гарант отработал на все 100', date: '2026-02-02', rating: 5, hasHeart: true },
    { username: 'apex', gift: 'Astral Shard', text: 'сделка на Astral Shard прошла, чуть подтупливал бот но деньги дошли', date: '2026-07-09', rating: 4 },
    { username: 'gift_hunter', gift: 'Loot Bag', text: 'сделка на Loot Bag прошла успешно, гарант отработал на все 100', date: '2026-03-02', rating: 5 },
    { username: 'sigma_boy_alik', gift: 'Homemade Cake', text: 'гарант держал Homemade Cake пока переводил деньги, потом отдал. надёжно', date: '2026-03-26', rating: 5 },
    { username: 'donttrust', gift: 'Star Notepad', text: 'Star Notepad купил, всё честно, никто никого не наебал. рекомендую', date: '2026-06-06', rating: 5 },
    { username: 'печенька', gift: 'Restless Jar', text: 'забрал Restless Jar после оплаты, бот не отпустил пока не заплатил. топ', date: '2026-06-26', rating: 5 },
    { username: 'shadow', gift: 'Crystal Ball', text: 'сделка на Crystal Ball прошла успешно, гарант отработал на все 100', date: '2026-05-22', rating: 5 },
    { username: 'shadow', gift: 'Kissed Frog', text: 'оплата за Kissed Frog зависла, писал в поддержку пока решили', date: '2026-06-19', rating: 2 },
    { username: 'biba756', gift: 'Flying Broom', text: 'продавец кинул Flying Broom в гаранта, оплатил и сразу получил. быстро', date: '2026-05-01', rating: 5 },
    { username: 'fenix641', gift: 'Santa Hat', text: 'гарант держал Santa Hat пока переводил деньги, потом отдал. надёжно', date: '2026-01-21', rating: 5 },
    { username: 'pepe_lord_apex', gift: 'Magic Potion', text: 'сделка на Magic Potion прошла, чуть подтупливал бот но деньги дошли', date: '2026-04-10', rating: 4 },
    { username: 'hodl', gift: 'Kissed Frog', text: 'Kissed Frog продал, покупатель забрал из бота и мне упали бабки. чётко', date: '2026-05-26', rating: 5 },
    { username: 'xdmen', gift: 'Hanging Star', text: 'купил Hanging Star, гарант ок но минут 20 ждал пока продавец закинет', date: '2026-07-07', rating: 4 },
    { username: 'батя_2', gift: 'Berry Box', text: 'купил Berry Box, продавец закинул в бота и я спокойно оплатил. всё чисто', date: '2026-04-08', rating: 5 },
    { username: 'nikitos270', gift: 'Ginger Cookie', text: 'купил Ginger Cookie, гарант ок но минут 20 ждал пока продавец закинет', date: '2026-06-05', rating: 4 },
    { username: 'nikitos', gift: 'Jelly Bunny', text: 'escrow для телеги подарков реально работает, Jelly Bunny прошёл гладко', date: '2026-06-28', rating: 5 },
    { username: 'pepe_lord', gift: 'Westside Sign', text: 'гарант держал Westside Sign пока переводил деньги, потом отдал. надёжно', date: '2026-03-19', rating: 5 },
    { username: 'lolz_fan', gift: 'Sky Stilettos', text: 'Sky Stilettos купил, всё честно, никто никого не наебал. рекомендую', date: '2026-06-13', rating: 5 },
    { username: 'softy_donttrust', gift: 'Heroic Helmet', text: 'брал Heroic Helmet, в лс бы не рискнул, а тут бот держал сделку. спокойно', date: '2026-01-21', rating: 5 },
    { username: 'босс', gift: 'Durov\'s Cap', text: 'escrow для телеги подарков реально работает, Durov\'s Cap прошёл гладко', date: '2026-06-06', rating: 5 },
    { username: 'сынбога', gift: 'Ginger Cookie', text: 'сделка на Ginger Cookie прошла, чуть подтупливал бот но деньги дошли', date: '2026-06-22', rating: 4 },
    { username: 'gift_hunter_pepe_lord', gift: 'Bonded Ring', text: 'забрал Bonded Ring после оплаты, бот не отпустил пока не заплатил. топ', date: '2026-07-04', rating: 5 },
    { username: 'donttrust', gift: 'Perfume Bottle', text: 'bought Perfume Bottle, seller dropped it in the bot and i paid safely', date: '2026-07-08', rating: 5 },
    { username: 'denchik', gift: 'Eternal Rose', text: 'продавец кинул Eternal Rose в гаранта, оплатил и сразу получил. быстро', date: '2026-04-22', rating: 5, hasHeart: true },
    { username: 'tg_gifts543', gift: 'Precious Peach', text: 'брал Precious Peach, в лс бы не рискнул, а тут бот держал сделку. спокойно', date: '2026-06-04', rating: 5 },
    { username: 'just_ok_dread', gift: 'Toy Bear', text: 'оплата за Toy Bear зависла, писал в поддержку пока решили', date: '2026-02-06', rating: 2 },
    { username: 'shadow', gift: 'Electric Skull', text: 'продал Electric Skull, норм но комса кусается немного', date: '2026-01-09', rating: 4 },
    { username: 'tradermax_glebrus', gift: 'Snoop Dogg', text: 'Snoop Dogg забрал, всё нормально, но интерфейс мог быть попроще', date: '2026-06-12', rating: 4 },
    { username: 'царь_x', gift: 'Jack-in-the-Box', text: 'Jack-in-the-Box купил, деньги шли долго, но в итоге всё ок', date: '2026-04-20', rating: 3 },
    { username: 'pepe_lord', gift: 'Heroic Helmet', text: 'sold Heroic Helmet via the bot, escrow held funds until paid. smooth', date: '2026-07-12', rating: 5 },
    { username: 'apex', gift: 'Flying Broom', text: 'got Flying Broom after payment, guarantor worked fine. recommend', date: '2026-05-01', rating: 5 },
    { username: 'lolz_fan', gift: 'Magic Potion', text: 'брал Magic Potion, в лс бы не рискнул, а тут бот держал сделку. спокойно', date: '2026-06-28', rating: 5 },
    { username: 'kirscht', gift: 'Eternal Rose', text: 'Eternal Rose — сделка тормозила, в итоге разрулили но осадок остался', date: '2026-02-24', rating: 1 },
    { username: 'tg_gifts415', gift: 'Top Hat', text: 'сделка на Top Hat прошла, чуть подтупливал бот но деньги дошли', date: '2026-07-10', rating: 4 },
    { username: 'gift_hunter', gift: 'Berry Box', text: 'купил Berry Box, гарант ок но минут 20 ждал пока продавец закинет', date: '2026-02-08', rating: 4 },
    { username: 'daniil390', gift: 'Low Rider', text: 'Low Rider купил, всё честно, никто никого не наебал. рекомендую', date: '2026-05-17', rating: 5 },
    { username: 'yellow', gift: 'Restless Jar', text: 'Restless Jar купил, всё честно, никто никого не наебал. рекомендую', date: '2026-01-03', rating: 5, hasHeart: true },
    { username: 'дядя', gift: 'Evil Eye', text: 'Evil Eye купил, деньги шли долго, но в итоге всё ок', date: '2026-05-13', rating: 3 },
    { username: 'grimm506', gift: 'Party Sparkler', text: 'Party Sparkler купил, всё честно, никто никого не наебал. рекомендую', date: '2026-05-26', rating: 5 },
    { username: 'romka', gift: 'Jester Hat', text: 'продал Jester Hat тут, бот всё сам провёл. буду пользоваться ещё', date: '2026-06-21', rating: 5 },
    { username: 'kotik', gift: 'Spy Agaric', text: 'покупал Spy Agaric, деньги пришли не сразу но пришли. в целом норм', date: '2026-05-25', rating: 5 },
    { username: 'vasya', gift: 'Toy Bear', text: 'продал Toy Bear через бота, гарант держал пока платили. деньги пришли без косяков', date: '2026-06-05', rating: 5 },
    { username: 'серый_tg', gift: 'Mini Oscar', text: 'купил Mini Oscar, продавец закинул в бота и я спокойно оплатил. всё чисто', date: '2026-03-24', rating: 5 },
    { username: 'stasik535', gift: 'Party Sparkler', text: 'сделка на Party Sparkler прошла успешно, гарант отработал на все 100', date: '2026-01-24', rating: 5 },
    { username: 'дядя_tg', gift: 'Bow Tie', text: 'escrow для телеги подарков реально работает, Bow Tie прошёл гладко', date: '2026-04-18', rating: 5, hasHeart: true },
    { username: 'biba', gift: 'Top Hat', text: 'продал Top Hat тут, бот всё сам провёл. буду пользоваться ещё', date: '2026-07-09', rating: 5 },
    { username: 'misha600', gift: 'Spy Agaric', text: 'купил Spy Agaric, продавец закинул в бота и я спокойно оплатил. всё чисто', date: '2026-06-20', rating: 5 },
    { username: 'yellow_zloy', gift: 'Vintage Cigar', text: 'забрал Vintage Cigar после оплаты, бот не отпустил пока не заплатил. топ', date: '2026-06-13', rating: 5 },
    { username: 'zloy732', gift: 'Low Rider', text: 'купил Low Rider, продавец закинул в бота и я спокойно оплатил. всё чисто', date: '2026-06-01', rating: 5 },
    { username: 'just_ok192', gift: 'Bunny Muffin', text: 'Bunny Muffin купил, всё честно, никто никого не наебал. рекомендую', date: '2026-02-26', rating: 5 },
    { username: 'stasik206', gift: 'Sleigh Bell', text: 'Sleigh Bell продал, покупатель забрал из бота и мне упали бабки. чётко', date: '2026-02-10', rating: 5 },
    { username: 'olegg', gift: 'Cookie Heart', text: 'Cookie Heart купил, всё честно, никто никого не наебал. рекомендую', date: '2026-01-18', rating: 5 },
    { username: 'zaza', gift: 'Sharp Tongue', text: 'купил Sharp Tongue, продавец закинул в бота и я спокойно оплатил. всё чисто', date: '2026-06-13', rating: 5 },
    { username: 'glebrus371', gift: 'Flying Broom', text: 'продал Flying Broom через бота, гарант держал пока платили. деньги пришли без косяков', date: '2026-05-09', rating: 5 },
    { username: 'shadow', gift: 'Voodoo Doll', text: 'сделка на Voodoo Doll прошла, чуть подтупливал бот но деньги дошли', date: '2026-05-15', rating: 4 },
    { username: 'pepe_lord_serega', gift: 'Low Rider', text: 'купил Low Rider, продавец закинул в бота и я спокойно оплатил. всё чисто', date: '2026-06-08', rating: 5 },
    { username: 'zaza', gift: 'Swiss Watch', text: 'брал Swiss Watch, в лс бы не рискнул, а тут бот держал сделку. спокойно', date: '2026-05-15', rating: 5, hasHeart: true },
    { username: 'злодей', gift: 'Top Hat', text: 'Top Hat продал, покупатель забрал из бота и мне упали бабки. чётко', date: '2026-07-14', rating: 5 },
    { username: 'boba_neo', gift: 'Low Rider', text: 'сделка на Low Rider прошла успешно, гарант отработал на все 100', date: '2026-07-06', rating: 5 },
    { username: 'dread', gift: 'Diamond Ring', text: 'bought Diamond Ring, seller dropped it in the bot and i paid safely', date: '2026-06-05', rating: 5 },
    { username: 'softy318', gift: 'Durov\'s Cap', text: 'escrow для телеги подарков реально работает, Durov\'s Cap прошёл гладко', date: '2026-02-04', rating: 5 },
    { username: 'grimm', gift: 'Sleigh Bell', text: 'продавец кинул Sleigh Bell в гаранта, оплатил и сразу получил. быстро', date: '2026-03-24', rating: 5 },
    { username: 'shadow770', gift: 'Love Potion', text: 'Love Potion продал, покупатель забрал из бота и мне упали бабки. чётко', date: '2026-05-12', rating: 5 },
    { username: 'lolz_fan_maks_tg', gift: 'Hex Pot', text: 'сделка на Hex Pot прошла успешно, гарант отработал на все 100', date: '2026-06-18', rating: 5 },
    { username: 'nemki', gift: 'Switch Watchs', text: 'норм продал', date: '2026-07-09', rating: 5 },
    { username: 'simple', gift: 'Heroic Helmet', text: 'продаю и покупаю тут, escrow для телеги подарков', date: '2026-07-03', rating: 5 },
    { username: 'soft_demon', gift: 'Trapped Heart', text: 'забрал Trapped Heart после оплаты. бот не отпустил пока не заплатил', date: '2026-07-03', rating: 5 },
    { username: 'nemo', gift: 'Plush Pepe', text: 'продал пепу через бота, пока покупатель платил гарант держал, деньги пришли без косяков', date: '2026-06-30', rating: 5, hasHeart: true },
    { username: 'sutpa', gift: 'Durov\'s Cap', text: 'купил кепку, продавец закинул в бота и я спокойно оплатил. гарант норм', date: '2026-06-30', rating: 5 },
    { username: 'высоцкий', gift: 'Loot Bag', text: 'мешок брал, бот держал сделку пока переводил. в лс так бы не рискнул', date: '2026-06-29', rating: 5 },
    { username: 'vebber', gift: 'Swiss Watch', text: 'часы купил, гарант отработал но минут 20 ждал пока продавец закинет подарок', date: '2026-06-29', rating: 4 },
    { username: 'ivan_zolo', gift: 'Scared Cat', text: 'кота продал, покупатель забрал из бота и мне упали бабки. чисто', date: '2026-06-28', rating: 5 },
    { username: 'сын_собаки', gift: 'Homemade Cake', text: 'маме тортик брал, гарант держал пока оплачивал. удобно что не кидают', date: '2026-06-28', rating: 5 },
    { username: 'мама_мелва', gift: 'Magic Potion', text: 'зелье продала через бота. выплата пришла после того как покупатель забрал. меня советовал', date: '2026-06-27', rating: 4 },
    { username: 'rivultion', gift: 'Electric Skull', text: 'череп купил, продавец сначала в бота, потом я оплатил и забрал. как маркетплейс только для подарков', date: '2026-06-27', rating: 5 },
    { username: 'east_ace', gift: 'Genie Lamp', text: 'продаю и покупаю тут. ескоу для телеги подарков', date: '2026-06-26', rating: 5 },
    { username: 'black_eye', gift: 'Spiced Wine', text: 'сделка с spiced wine закрылась. гарант норм, коммуникация слабая', date: '2026-06-25', rating: 4 },
    { username: 'nissim', gift: 'Witch Hat', text: 'сделка чистая. ждал дольше чем хотелось', date: '2026-06-23', rating: 4 },
    { username: 'southsniper', gift: 'Jester Hat', text: 'гарант сработал, но минут 20 ждал ответа', date: '2026-06-22', rating: 4 },
    { username: 'леха', gift: 'Jelly Bunny', text: 'jelly bunny слал. гарант провёл. бабки на месте', date: '2026-06-20', rating: 5 },
    { username: 'Hobbit', gift: 'Witch Hat', text: 'гарант сработал, но минут 20 ждал ответа', date: '2026-06-20', rating: 4 },
    { username: 'bigclutch', gift: 'Party Sparkler', text: 'удобнее чем вручную договариваться с незнакомцем', date: '2026-06-18', rating: 5 },
    { username: 'icefox', gift: 'Spiced Wine', text: 'купил Spiced Wine, гарант ок но продавец долго кидал в бота', date: '2026-06-18', rating: 4 },
    { username: 'darksoul', gift: 'Love Potion', text: 'продал love potion, выплата пришла, минут 15 ждал покупателя', date: '2026-06-18', rating: 4 },
    { username: 'дровдер', gift: 'Electric Skull', text: 'сделка с Electric Skull закрылась. гарант норм, коммуникация слабая', date: '2026-06-17', rating: 4 },
    { username: 'gold_ace', gift: 'Jester Hat', text: 'гарант сработал, но минут 20 ждал ответа', date: '2026-06-16', rating: 4 },
    { username: 'sun_man', gift: 'Ginger Cookie', text: 'ginger cookie продал через гарант, не кидали ни меня ни покупателя', date: '2026-06-15', rating: 5 },
    { username: 'peekdragon', gift: 'Restless Jar', text: 'покупал restless jar, продавец кинул в escrow бота и я спокойно оплатил', date: '2026-06-12', rating: 5 },
    { username: 'swap_ton', gift: 'Magic Potion', text: 'выставил Magic Potion, бот держал пока покупатель платил', date: '2026-06-11', rating: 5 },
    { username: 'smokeman', gift: 'Perfume Bottle', text: 'взял Perfume Bottle, сначала подарок в боте потом платёж, норм схема', date: '2026-06-10', rating: 5 },
    { username: 'markiplier', gift: 'Spy Agaric', text: 'минут 5-10 и готово, гарант всё провёл', date: '2026-06-10', rating: 5 },
    { username: 'flash_dragon', gift: 'Toy Bear', text: 'гарант сработал, но минут 20 ждал ответа', date: '2026-06-09', rating: 4 },
    { username: 'big russian boss', gift: 'Top Hat', text: 'бот молчал потом провёл сделку, нервы были', date: '2026-06-07', rating: 4 },
    { username: 'sneakrifler', gift: 'Jingle Bells', text: 'в целом ок, гарант держит как надо', date: '2026-06-05', rating: 4 },
    { username: 'travian', gift: 'Trapped Heart', text: 'trapped heart, бот как посредник, без нервов', date: '2026-05-15', rating: 5 },
    { username: 'cs_gaules', gift: 'Desk Calendar', text: 'продаю и покупаю тут, escrow для телеги подарков ))', date: '2026-05-14', rating: 5 },
    { username: 'chillhawk', gift: 'Durov\'s Cap', text: 'продал Durov\'s Cap, выплата пришла, минут 15 ждал покупателя', date: '2026-05-14', rating: 4 },
    { username: 'deagle_run', gift: 'Jingle Bells', text: 'как фанней только для nft подарков, зашло', date: '2026-05-13', rating: 5 },
    { username: 'drop_line', gift: 'Magic Potion', text: 'сделка чистая, подарок не пропал по дороге', date: '2026-05-13', rating: 5 },
    { username: 'blackfox', gift: 'Flying Broom', text: 'продал Flying Broom, покупатель забрал из бота и мне упали деньги', date: '2026-05-13', rating: 5 },
    { username: 'miyagi', gift: 'Cupid Charm', text: 'бот молчал потом провёл сделку, нервы были', date: '2026-05-13', rating: 4 },
    { username: 'flash_master', gift: 'Swiss Watch', text: 'не с первого клика но подарок дошёл', date: '2026-05-13', rating: 4 },
    { username: 'gold_head', gift: 'Tama Gadget', text: 'отдал Tama Gadget в бота, деньги пришли после сделки', date: '2026-05-12', rating: 5 },
    { username: 'анстипопер', gift: 'Love Candle', text: 'минут 5-10 и готово, гарант всё провёл', date: '2026-05-12', rating: 5 },
    { username: 'hotrifler', gift: 'Party Sparkler', text: 'не первый раз, гарант всегда отрабатывает', date: '2026-05-12', rating: 5 },
    { username: 'komar', gift: 'Witch Hat', text: 'удобнее чем вручную договариваться с незнакомцем', date: '2026-05-11', rating: 5 },
    { username: 'coldrifler', gift: 'Xmas Stocking', text: 'xmas stocking купил через гарант, без бота в лс не стал бы', date: '2026-05-10', rating: 5 },
    { username: 'ace_eye', gift: 'Electric Skull', text: 'сливаешь подарок, ждёшь покупателя, бот всё фиксит', date: '2026-05-10', rating: 5 },
    { username: 'sneaksoul', gift: 'Diamond Ring', text: 'брал Diamond Ring, в итоге всё ок, чуть дольше обычного', date: '2026-05-10', rating: 4 },
    { username: 'moist', gift: 'Lunar Snake', text: 'третий обмен уже, гарант не подводил', date: '2026-05-09', rating: 5 },
    { username: 'night_star', gift: 'Record Player', text: 'Record Player продал, деньги пришли, не моментально', date: '2026-05-08', rating: 4 },
    { username: 'slow_hunter', gift: 'Nail Bracelet', text: 'удобнее чем вручную договариваться с незнакомцем', date: '2026-05-08', rating: 5 },
    { username: 'moon_core', gift: 'Neko Helmet', text: 'третий обмен уже, гарант не подводил', date: '2026-05-08', rating: 5 },
    { username: 'toxic', gift: 'Neko Helmet', text: 'бот молчал потом провёл сделку, нервы были', date: '2026-05-07', rating: 4 },
    { username: 'chillclutch', gift: 'Loot Bag', text: 'сделка с Loot Bag закрылась, гарант норм, коммуникация слабая', date: '2026-05-06', rating: 4 },
    { username: 'markul', gift: 'Input Key', text: 'Input Key купил через гарант, без бота в лс не стал бы', date: '2026-05-05', rating: 5 },
    { username: 'big_zone', gift: 'Nail Bracelet', text: 'не первый раз, гарант всегда отрабатывает', date: '2026-05-05', rating: 5 },
    { username: 'darkfox', gift: 'Tama Gadget', text: 'сделка чистая, подарок не пропал по дороге', date: '2026-05-05', rating: 5 },
    { username: 'smoke_flash', gift: 'Jelly Bunny', text: 'jelly bunny продал через гарант', date: '2026-05-05', rating: 5 },
    { username: 'lil_hand', gift: 'Magic Potion', text: 'Magic Potion, бот как посредник, без нервов', date: '2026-05-02', rating: 5 },
    { username: 'west_rifler', gift: 'Cupid Charm', text: 'сделка чистая, ждал дольше чем хотелось', date: '2026-05-02', rating: 4 },
    { username: 'white_angel', gift: 'Nail Bracelet', text: 'оплатил и Nail Bracelet прилетел, гарант отработал как надо', date: '2026-05-01', rating: 5 },
    { username: 'fine_flash', gift: 'Tama Gadget', text: 'в целом ок, гарант держит как надо', date: '2026-05-01', rating: 4 },
    { username: 'edisonpts', gift: 'Perfume Bottle', text: 'продавец закинул, я оплатил, забрал, всё', date: '2026-05-01', rating: 5 },
    { username: 'storm_dog', gift: 'Signet Ring', text: 'signet ring продал без проблем, деньги пришли в бота', date: '2026-04-29', rating: 5 },
    { username: 'slysniper', gift: 'Eternal Rose', text: 'удобнее чем вручную договариваться с незнакомцем', date: '2026-04-29', rating: 5 },
    { username: 'forcedog', gift: 'Jelly Bunny', text: 'купил jelly bunny, гарант ок но продавец долго кидал в бота', date: '2026-04-29', rating: 4 },
    { username: 'steel_peek', gift: 'Signet Ring', text: 'сделка чистая, подарок не пропал по дороге лол', date: '2026-04-29', rating: 5 },
    { username: 'real_line', gift: 'Moon Pendant', text: 'бот не отпускает подарок пока не оплатишь, топ', date: '2026-04-28', rating: 5 },
    { username: 'sly_head', gift: 'Flying Broom', text: 'гарант сработал, но минут 20 ждал ответа', date: '2026-04-28', rating: 4 },
    { username: 'starflex', gift: 'Joyful Bundle', text: 'продавец закинул, я оплатил, забрал, всё', date: '2026-04-28', rating: 5 },
    { username: 'ghost_man', gift: 'Kissed Frog', text: 'оплатил и Kissed Frog прилетел, гарант отработал как надо', date: '2026-04-27', rating: 5 },
    { username: 'south_dragon', gift: 'Perfume Bottle', text: 'брал Perfume Bottle, гарант держал пока переводил, всё чётко', date: '2026-04-27', rating: 5 },
    { username: 'south', gift: 'Scared Cat', text: 'продал scared cat, выплата пришла, минут 15 ждал покупателя', date: '2026-04-27', rating: 4 },
    { username: 'ace_lurker', gift: 'Star Notepad', text: 'продаю и покупаю тут, escrow для телеги подарков', date: '2026-04-26', rating: 5 },
    { username: 'southrat', gift: 'Durov\'s Cap', text: 'Durov\'s Cap, бот как посредник, без нервов', date: '2026-04-26', rating: 5 },
    { username: 'red_mind', gift: 'Mad Pumpkin', text: 'продал Mad Pumpkin, покупатель забрал из бота и мне упали деньги', date: '2026-04-25', rating: 5 },
    { username: 'southgod', gift: 'Skull Flower', text: 'брал Skull Flower, гарант держал пока переводил, всё чётко', date: '2026-04-25', rating: 5 },
    { username: 'smoker', gift: 'Mad Pumpkin', text: 'mad pumpkin прилетел, нормально', date: '2026-04-22', rating: 4 },
    { username: 'fragman', gift: 'Moon Pendant', text: 'сливаешь подарок, ждёшь покупателя, бот всё фиксит', date: '2026-04-21', rating: 5 },
    { username: 'chillboy', gift: 'Record Player', text: 'бот не отпускает подарок пока не оплатишь, топ', date: '2026-04-21', rating: 5 },
    { username: 'frag_kid', gift: 'Love Candle', text: 'сделка с love candle закрылась, гарант норм, коммуникация слабая', date: '2026-04-20', rating: 4 },
    { username: 'wolf_head', gift: 'Holiday Drink', text: 'в целом ок, гарант держит как надо', date: '2026-04-20', rating: 4 },
    { username: 'bluerat', gift: 'Star Notepad', text: 'Star Notepad продал, деньги пришли, не моментально', date: '2026-04-20', rating: 4 },
    { username: 'kinq', gift: 'Light Sword', text: 'Light Sword продал, деньги пришли, не моментально', date: '2026-04-20', rating: 4 },
    { username: 'force_team', gift: 'Sharp Tongue', text: 'бот держит подарок пока платите, удобная тема', date: '2026-04-17', rating: 5 },
    { username: 'eco_smoke', gift: 'Love Potion', text: 'отдал Love Potion в бота, деньги пришли после сделки', date: '2026-04-17', rating: 5 },
    { username: 'lowcore', gift: 'Desk Calendar', text: 'Desk Calendar купил через гарант, без бота в лс не стал бы', date: '2026-04-16', rating: 5 },
    { username: 'clutch_team', gift: 'Spy Agaric', text: 'Spy Agaric купил через гарант, без бота в лс не стал бы', date: '2026-04-16', rating: 5 },
    { username: 'chill_support', gift: 'Plush Pepe', text: 'продавец тупил но бот сделку не потерял', date: '2026-04-16', rating: 4 },
    { username: 'redking', gift: 'Star Notepad', text: 'покупал Star Notepad, продавец кинул в escrow бота и я спокойно оплатил', date: '2026-04-16', rating: 5 },
    { username: 'ace_master', gift: 'Spiced Wine', text: 'забрал Spiced Wine после оплаты, бот не отпустил пока не заплатил', date: '2026-04-06', rating: 5 },
    { username: 'unluckyman', gift: 'Love Candle', text: 'брал Love Candle, гарант держал пока переводил, всё чётко', date: '2026-04-06', rating: 5 },
    { username: 'gold_master', gift: 'Jingle Bells', text: 'сделка с Jingle Bells закрылась, гарант норм, коммуникация слабая', date: '2026-04-05', rating: 4 },
    { username: 'wildeye', gift: 'Restless Jar', text: 'продал restless jar, покупатель забрал из бота и мне упали деньги', date: '2026-04-05', rating: 5 },
    { username: 'deagle_shot', gift: 'Input Key', text: 'как фанней только для nft подарков, зашло', date: '2026-04-05', rating: 5 },
    { username: 'low_clutch', gift: 'Genie Lamp', text: 'купил genie lamp, гарант ок но продавец долго кидал в', date: '2026-04-06', rating: 4 }
];

// Star rating functionality
document.addEventListener('DOMContentLoaded', function() {
    // Заполняем поле Ник автоматически из Telegram
    document.getElementById('nickname-input').value = username;
    document.getElementById('nickname-input').disabled = true; // Запрещаем редактирование

    loadProfile(); // включит или заблокирует форму, когда сервер посчитает сделки

    const starInputs = document.querySelectorAll('.star-input');
    let selectedRating = 0;

    starInputs.forEach((star, index) => {
        // Hover effect
        star.addEventListener('mouseenter', function() {
            highlightStars(index + 1);
        });

        // Click to select
        star.addEventListener('click', function() {
            selectedRating = index + 1;
            highlightStars(selectedRating);
        });
    });

    // Reset on mouse leave
    const starRating = document.querySelector('.star-rating');
    starRating.addEventListener('mouseleave', function() {
        highlightStars(selectedRating);
    });

    function highlightStars(count) {
        starInputs.forEach((star, index) => {
            if (index < count) {
                star.classList.add('active');
            } else {
                star.classList.remove('active');
            }
        });
    }

    // Sort reviews by date (newest first) and load
    sortAndLoadReviews(); // Вызываем async функцию
    
    // Update review counts on page load
    updateReviewCount();

    // Initialize gift dropdown
    initGiftDropdown();

    // Initialize scroll animations
    observeElements();

    // Language switcher
    document.querySelectorAll('.lang-switch__btn').forEach(btn => {
        btn.addEventListener('click', function() {
            // Убираем активный класс у всех кнопок
            document.querySelectorAll('.lang-switch__btn').forEach(b => b.classList.remove('is-active'));
            // Добавляем активный класс текущей кнопке
            this.classList.add('is-active');
            // Обновляем язык
            updateLanguage(this.dataset.lang);
        });
    });

    // Character counter for textarea
    const textInput = document.getElementById('text-input');
    const charCount = document.getElementById('char-count');
    const charCounter = document.querySelector('.char-counter');

    textInput.addEventListener('input', function() {
        const length = this.value.length;
        charCount.textContent = length;

        if (length > 50) {
            // Truncate to 50 characters
            this.value = this.value.substring(0, 50);
            charCount.textContent = 50;
        }

        if (length >= 45) {
            charCounter.classList.add('error');
            charCounter.classList.remove('success');
        } else {
            charCounter.classList.remove('error');
            if (length > 0) {
                charCounter.classList.add('success');
            } else {
                charCounter.classList.remove('success');
            }
        }
    });

    // Form submission
    const submitButton = document.querySelector('.submit-button');
    submitButton.addEventListener('click', async function(e) {
        e.preventDefault();

        // Сервер проверит это ещё раз, здесь — чтобы не гонять заведомо отказной запрос
        const blocked = gateMessage();
        if (blocked) {
            tg.showAlert(blocked);
            return;
        }

        const gift = document.getElementById('gift-input-hidden').value;
        const reviewText = document.getElementById('text-input').value;

        if (selectedRating === 0) {
            tg.showAlert('Пожалуйста, выберите оценку');
            return;
        }

        if (!gift.trim()) {
            tg.showAlert('Пожалуйста, выберите подарок');
            return;
        }

        if (!reviewText.trim()) {
            tg.showAlert('Пожалуйста, напишите текст отзыва');
            return;
        }

        if (reviewText.trim().length > 50) {
            tg.showAlert('Текст отзыва не должен превышать 50 символов');
            return;
        }

        // Ник сервер подставит сам из подписи Telegram — отсюда его не шлём
        const reviewData = {
            initData: initData,
            gift: gift,
            text: reviewText,
            rating: selectedRating
        };

        // Отправляем данные через Telegram Web App API
        try {
            // Отправляем на сервер
            const response = await fetch('/api/submit-review', {
                method: 'POST',
                headers: authHeaders({ 'Content-Type': 'application/json' }),
                body: JSON.stringify(reviewData)
            });

            if (response.ok) {
                // Показываем уведомление об успехе
                tg.showAlert('✅ Спасибо за ваш отзыв!');

                // Закрываем мини-приложение
                setTimeout(() => {
                    tg.close();
                }, 1500);
                return;
            }

            // Сделок стало меньше порога или подпись протухла — обновляем состояние формы
            if (response.status === 401 || response.status === 403 || response.status === 503) {
                await loadProfile();
                tg.showAlert(gateMessage() || '❌ Ошибка при отправке отзыва');
                return;
            }

            tg.showAlert('❌ Ошибка при отправке отзыва');
        } catch (error) {
            console.error('Error:', error);
            tg.showAlert('❌ Ошибка при отправке отзыва');
        }
    });
});

// Сравниваем с концом текущего дня, а не с текущим часом: расхождение
// часовых поясов с сервером не должно прятать только что оставленный отзыв
function isFutureDate(dateStr) {
    if (!dateStr) return false;
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return false;
    const endOfToday = new Date();
    endOfToday.setHours(23, 59, 59, 999);
    return date > endOfToday;
}

async function sortAndLoadReviews() {
    let customReviewsCount = 0;
    let customReviews = [];

    // Витринные отзывы с датой из будущего не показываем: такой сделки ещё не было
    for (let i = reviewsData.length - 1; i >= 0; i--) {
        if (!reviewsData[i].isCustom && isFutureDate(reviewsData[i].date)) {
            reviewsData.splice(i, 1);
        }
    }

    // Загружаем custom отзывы из txt файла
    try {
        // Сервер вернёт только отзывы этого пользователя: чужие никому не видны
        const response = await fetch('/api/get-custom-reviews', { headers: authHeaders() });
        if (response.ok) {
            const data = await response.json();
            if (data.reviews && data.reviews.length > 0) {
                customReviewsCount = data.reviews.length;
                customReviews = data.reviews;
                
                // Сортируем custom отзывы по дате (новые первыми)
                customReviews.sort((a, b) => {
                    if (!a.date) return 1;
                    if (!b.date) return -1;
                    return new Date(b.date) - new Date(a.date);
                });
                
                // Подсветка «⭐ Новый» — только на отзывах текущего пользователя.
                // Раньше её видели все на самом свежем отзыве, чужом в том числе.
                let ownMarked = false;
                customReviews.forEach(review => {
                    const isOwn = review.username === username;
                    review.isNew = isOwn;
                    // «Недавно» вместо даты — на самом свежем СВОЁМ отзыве
                    review.showRecent = isOwn && !ownMarked;
                    if (isOwn) ownMarked = true;
                });

                // Свои отзывы поднимаем над чужими, чтобы человек сразу видел свой
                customReviews.sort((a, b) => {
                    const aOwn = a.username === username ? 1 : 0;
                    const bOwn = b.username === username ? 1 : 0;
                    return bOwn - aOwn;
                });

                // unshift переворачивает порядок, поэтому идём с конца
                for (let i = customReviews.length - 1; i >= 0; i--) {
                    reviewsData.unshift(customReviews[i]);
                }
                
                console.log(`Loaded ${customReviewsCount} custom reviews`);
            }
        }
    } catch (error) {
        console.error('Failed to load custom reviews:', error);
    }
    
    // Обновляем РЕАЛЬНЫЙ счётчик отзывов (фактическое количество в массиве)
    totalReviewsCount = reviewsData.length;
    
    // Sort by date (newest first)
    reviewsData.sort((a, b) => {
        // Свой отзыв — всегда самый первый, чтобы не искать его в списке
        const aOwn = a.username === username ? 1 : 0;
        const bOwn = b.username === username ? 1 : 0;
        if (aOwn !== bOwn) return bOwn - aOwn;
        if (a.isCustom && !b.isCustom) return -1; // Custom отзывы всегда первые
        if (!a.isCustom && b.isCustom) return 1;
        return new Date(b.date) - new Date(a.date);
    });
    
    loadReviews();
    
    // Обновляем счётчики после загрузки
    updateReviewCount();
}

function loadReviews() {
    const container = document.getElementById('reviews-container');
    container.innerHTML = '';

    // Показываем ВСЕ отзывы (реальное количество)
    reviewsData.forEach((review) => {
        const reviewElement = createReviewElement(review);
        container.appendChild(reviewElement);
    });
    
    // Запускаем наблюдение за новыми элементами
    observeElements();
}

function escapeHtml(value) {
    const holder = document.createElement('div');
    holder.textContent = value == null ? '' : String(value);
    return holder.innerHTML;
}

function createReviewElement(review) {
    const reviewDiv = document.createElement('div');
    reviewDiv.className = 'review-item';

    // Проверяем, является ли это отзывом текущего пользователя
    if (review.username === username) {
        reviewDiv.classList.add('review-item--own');
    }
    
    // Добавляем класс "custom-review" (желтый фон) ТОЛЬКО для самого нового
    if (review.isNew) {
        reviewDiv.classList.add('custom-review');
    }

    const stars = generateStars(review.rating);
    const heartIcon = review.hasHeart ? '<span class="review-heart">💜</span>' : '';
    
    // Определяем дату для отображения
    let formattedDate;
    if (review.isCustom) {
        // Свой отзыв не удаляем из-за даты вперёд (часы сервера), но и не показываем её
        if (review.showRecent || !review.date || isFutureDate(review.date)) {
            formattedDate = 'Недавно';
        } else {
            formattedDate = formatDate(review.date);
        }
    } else {
        formattedDate = formatDate(review.date);
    }

    // Генерируем инициалы из имени пользователя (первые 2 буквы)
    const initials = escapeHtml(review.username.substring(0, 2).toUpperCase());

    reviewDiv.innerHTML = `
        <div class="review-top">
            <div class="review-left">
                <div class="review-avatar">
                    ${initials}
                </div>
                <div class="review-user-info">
                    <div class="review-username">
                        ${escapeHtml(review.username)}
                        ${heartIcon}
                    </div>
                    <a href="#" class="review-gift">${escapeHtml(review.gift)}</a>
                </div>
            </div>
            <div class="review-stars">${stars}</div>
        </div>
        <p class="review-text">${escapeHtml(review.text)}</p>
        <span class="review-date">${escapeHtml(formattedDate)}</span>
    `;

    return reviewDiv;
}

function generateStars(rating) {
    let stars = '';
    for (let i = 1; i <= 5; i++) {
        if (i <= rating) {
            stars += '<span class="review-star">★</span>';
        } else {
            stars += '<span class="review-star empty">☆</span>';
        }
    }
    return stars;
}

function formatDate(dateStr) {
    const months = ['янв.', 'фев.', 'мар.', 'апр.', 'мая', 'июн.', 'июл.', 'авг.', 'сен.', 'окт.', 'ноя.', 'дек.'];
    const date = new Date(dateStr);
    const day = date.getDate();
    const month = months[date.getMonth()];
    const year = date.getFullYear();
    return `${day} ${month} ${year} г.`;
}

function updateReviewCount() {
    const totalCountElement = document.getElementById('total-reviews-count');
    const sectionCountElement = document.getElementById('reviews-section-count');
    const shownCountElement = document.getElementById('shown-reviews-count');
    const footerTotalElement = document.getElementById('footer-total-count');

    // РЕАЛЬНОЕ количество отзывов для показа (все что есть в массиве)
    const shownCount = Math.min(reviewsData.length, totalReviewsCount);

    if (totalCountElement) {
        totalCountElement.textContent = totalReviewsCount.toLocaleString('ru-RU');
    }

    if (sectionCountElement) {
        sectionCountElement.textContent = totalReviewsCount.toLocaleString('ru-RU');
    }

    if (shownCountElement) {
        shownCountElement.textContent = shownCount.toLocaleString('ru-RU');
    }
    
    if (footerTotalElement) {
        footerTotalElement.textContent = totalReviewsCount.toLocaleString('ru-RU');
    }
}

// Gift dropdown functionality
function initGiftDropdown() {
    const giftSelectBox = document.getElementById('gift-select-box');
    const giftSelectText = document.getElementById('gift-select-text');
    const giftInputHidden = document.getElementById('gift-input-hidden');
    const giftDropdown = document.getElementById('gift-dropdown');
    const giftSearchInput = document.getElementById('gift-search-input');
    const giftOptionsList = document.getElementById('gift-options-list');

    // Populate dropdown with all gifts
    giftItems.forEach(gift => {
        const option = document.createElement('div');
        option.className = 'gift-option';
        option.textContent = `🎁 ${gift}`;
        option.dataset.value = gift;
        
        option.addEventListener('click', function() {
            giftSelectText.textContent = gift;
            giftSelectText.classList.add('selected');
            giftInputHidden.value = gift;
            closeDropdown();
        });
        
        giftOptionsList.appendChild(option);
    });

    // Toggle dropdown on box click
    giftSelectBox.addEventListener('click', function(e) {
        e.stopPropagation();
        toggleDropdown();
    });

    // Filter gifts on search input
    giftSearchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        filterGifts(searchTerm);
    });

    // Prevent dropdown close when clicking search input
    giftSearchInput.addEventListener('click', function(e) {
        e.stopPropagation();
    });

    // Hide dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.gift-select-wrapper')) {
            closeDropdown();
        }
    });

    function toggleDropdown() {
        const isOpen = giftDropdown.classList.contains('show');
        if (isOpen) {
            closeDropdown();
        } else {
            openDropdown();
        }
    }

    function openDropdown() {
        giftDropdown.classList.add('show');
        giftSelectBox.classList.add('active');
        giftSearchInput.value = '';
        filterGifts('');
        setTimeout(() => giftSearchInput.focus(), 100);
    }

    function closeDropdown() {
        giftDropdown.classList.remove('show');
        giftSelectBox.classList.remove('active');
        giftSearchInput.value = '';
    }
}

function filterGifts(searchTerm) {
    const options = document.querySelectorAll('.gift-option');

    options.forEach(option => {
        const giftName = option.dataset.value.toLowerCase();
        if (giftName.includes(searchTerm)) {
            option.classList.remove('hidden');
        } else {
            option.classList.add('hidden');
        }
    });
}



// ========== ВОЛНОВАЯ АНИМАЦИЯ ПОЯВЛЕНИЯ ОТЗЫВОВ ==========
function addReviewsWaveAnimation() {
    const reviews = document.querySelectorAll('.review-item');
    
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry, index) => {
            if (entry.isIntersecting) {
                setTimeout(() => {
                    entry.target.classList.add('show');
                }, index * 50); // Задержка между элементами
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    reviews.forEach(review => {
        observer.observe(review);
    });
}

// Вызываем функцию после загрузки отзывов
setTimeout(addReviewsWaveAnimation, 500);

// ========== ЭФФЕКТ RIPPLE ДЛЯ КНОПКИ ==========
document.addEventListener('DOMContentLoaded', function() {
    const submitBtn = document.querySelector('.submit-button');
    
    if (submitBtn) {
        submitBtn.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.style.position = 'absolute';
            ripple.style.borderRadius = '50%';
            ripple.style.background = 'rgba(255, 255, 255, 0.6)';
            ripple.style.transform = 'scale(0)';
            ripple.style.animation = 'ripple 0.6s ease-out';
            ripple.style.pointerEvents = 'none';
            
            this.appendChild(ripple);
            
            setTimeout(() => ripple.remove(), 600);
        });
    }
    
    // Добавляем CSS для ripple анимации
    const style = document.createElement('style');
    style.textContent = `
        @keyframes ripple {
            to {
                transform: scale(2);
                opacity: 0;
            }
        }
        
        .submit-button {
            position: relative;
            overflow: hidden;
        }
    `;
    document.head.appendChild(style);
});


// Тема только тёмная — переключатель удалён.
