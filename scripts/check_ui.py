import json
from pathlib import Path
from playwright.sync_api import sync_playwright

output = Path('artifacts')
output.mkdir(exist_ok=True)


def assert_storefront_styles(page):
    """A 200 response alone does not catch unstyled third-party templates."""
    metrics = page.evaluate('''() => {
        const main = document.querySelector('#main.main-content');
        const header = document.querySelector('header.header');
        const stylesheet = [...document.querySelectorAll('link[rel="stylesheet"]')]
            .find(link => /\\/static\\/css\\/style(?:\\.[a-f0-9]+)?\\.css/.test(link.href));
        return {
            shell: !!main && !!header && !!document.querySelector('#sidebar'),
            stylesheetLoaded: !!stylesheet?.sheet?.cssRules.length,
            headerDisplay: header && getComputedStyle(header).display,
            mainPadding: main && parseFloat(getComputedStyle(main).paddingLeft),
            viewport: document.documentElement.clientWidth,
            contentWidth: document.documentElement.scrollWidth,
        };
    }''')
    assert metrics['shell'], (page.url, metrics)
    assert metrics['stylesheetLoaded'], (page.url, metrics)
    assert metrics['headerDisplay'] == 'flex', (page.url, metrics)
    assert metrics['mainPadding'] > 0, (page.url, metrics)
    assert metrics['contentWidth'] <= metrics['viewport'], (page.url, metrics)


with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    page = browser.new_page(viewport={'width':1440,'height':1100}, device_scale_factor=1)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    response=page.goto('http://127.0.0.1:8080/', wait_until='networkidle')
    print('HOME', response.status)
    assert_storefront_styles(page)
    page.screenshot(path=str(output/'desktop.png'), full_page=True)
    print('TITLE',page.title())
    assert '拉拉熊' in page.title()
    old_images = page.locator('img').evaluate_all('(els)=>els.map(e=>e.src).filter(src=>/\/(hero|bunny|bear|cat|cup)\\.png(?:$|\\?)/.test(src))')
    assert not old_images, old_images
    broken=page.locator('img:visible').evaluate_all('(els)=>els.filter(e=>e.complete&&e.naturalWidth===0).map(e=>e.src)')
    print('BROKEN_VISIBLE_IMAGES',broken)
    assert not broken,broken
    reports=[]
    for width in (1440,1024,768,390,320):
        page.set_viewport_size({'width':width,'height':900})
        page.goto('http://127.0.0.1:8080/',wait_until='networkidle')
        assert_storefront_styles(page)
        reports.append({'width':width,'scrollWidth':page.evaluate('document.documentElement.scrollWidth')})
        if width==390:
            page.screenshot(path=str(output/'mobile.png'),full_page=True)
            page.locator('#menuToggle').click()
            assert page.locator('#sidebar').evaluate('(el)=>el.classList.contains("is-open")')
            page.screenshot(path=str(output/'mobile-menu.png'),full_page=True)
            page.keyboard.press('Escape')
    print('RESPONSIVE',json.dumps(reports))
    for width in (1440,1024,768,390,320):
        page.set_viewport_size({'width':width,'height':1000})
        for route in ('/products/','/products/category/dolls/','/products/rilakkuma-raincoat/',
                      '/accounts/login/','/accounts/signup/','/orders/cart/','/orders/wish/',
                      '/about/','/notice/','/accounts/password/reset/',
                      '/accounts/password/reset/done/','/accounts/inactive/',
                      '/orders/','/orders/wish/create/'):
            response=page.goto('http://127.0.0.1:8080'+route,wait_until='networkidle')
            print('ROUTE',width,route,response.status)
            assert response.status==200,(route,response.status)
            assert_storefront_styles(page)
    page.set_viewport_size({'width':1440,'height':1000})
    page.goto('http://127.0.0.1:8080/products/rilakkuma-raincoat/',wait_until='networkidle')
    page.locator('[data-qty-step="1"]').click()
    page.get_by_role('button',name='加入購物車',exact=True).click()
    page.wait_for_function('document.querySelector(".cart-badge").textContent==="2"')
    page.goto('http://127.0.0.1:8080/orders/cart/',wait_until='networkidle')
    assert page.locator('.cart-item input').input_value()=='2'
    page.locator('[data-cart-step="1"]').click()
    page.wait_for_function('document.querySelector(".cart-item input").value==="3"')
    page.screenshot(path=str(output/'cart.png'),full_page=True)
    page.locator('[data-remove]').click()
    page.get_by_text('留一點空間，給新的喜歡。').wait_for()
    print('CART_FLOW','passed')
    print('JS_ERRORS',errors)
    assert not errors,errors
    assert all(row['scrollWidth']<=row['width'] for row in reports),reports
    browser.close()
