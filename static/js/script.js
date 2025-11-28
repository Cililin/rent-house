// static/js/script.js
// 确保DOM加载完成后初始化所有组件
document.addEventListener('DOMContentLoaded', function() {
    // 初始化所有轮播组件
    var carousels = document.querySelectorAll('.carousel');
    carousels.forEach(function(carousel) {
        try {
            if (typeof bootstrap !== 'undefined' && bootstrap.Carousel) {
                new bootstrap.Carousel(carousel, {
                    interval: 5000,
                    pause: 'hover',
                    wrap: true
                });
            }
        } catch (error) {
            console.error('Error initializing carousel:', error);
        }
    });
});


// 搜索自动完成
function initSearchAutocomplete() {
    const searchInput = document.querySelector('input[name="keyword"]');
    if (!searchInput) return;

    let timeout;

    searchInput.addEventListener('input', function() {
        clearTimeout(timeout);
        const query = this.value.trim();

        if (query.length < 2) {
            hideAutocomplete();
            return;
        }

        timeout = setTimeout(() => {
            fetchAutocompleteSuggestions(query);
        }, 200);
    });

    searchInput.addEventListener('keydown', function(e) {
        const suggestions = document.querySelector('.autocomplete-suggestions');
        if (!suggestions) return;

        const items = suggestions.querySelectorAll('.autocomplete-item');
        let activeItem = suggestions.querySelector('.autocomplete-item.active');

        switch(e.key) {
            case 'ArrowDown':
                e.preventDefault();
                if (!activeItem) {
                    items[0]?.classList.add('active');
                } else {
                    activeItem.classList.remove('active');
                    const next = activeItem.nextElementSibling || items[0];
                    next.classList.add('active');
                }
                break;

            case 'ArrowUp':
                e.preventDefault();
                if (activeItem) {
                    activeItem.classList.remove('active');
                    const prev = activeItem.previousElementSibling || items[items.length - 1];
                    prev.classList.add('active');
                }
                break;

            case 'Enter':
                if (activeItem) {
                    e.preventDefault();
                    activeItem.click();
                }
                break;

            case 'Escape':
                hideAutocomplete();
                break;
        }
    });
}

function fetchAutocompleteSuggestions(query) {
    fetch(`/api/search_suggest?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(suggestions => {
            showAutocompleteSuggestions(suggestions);
        })
        .catch(error => console.error('Error:', error));
}

function showAutocompleteSuggestions(suggestions) {
    hideAutocomplete();

    if (suggestions.length === 0) return;

    const searchInput = document.querySelector('input[name="keyword"]');
    const container = document.createElement('div');
    container.className = 'autocomplete-suggestions card position-absolute w-100';
    container.style.cssText = `
        z-index: 1050;
        top: 100%;
        left: 0;
        max-height: 300px;
        overflow-y: auto;
    `;

    suggestions.forEach((suggestion, index) => {
        const item = document.createElement('a');
        item.className = `autocomplete-item list-group-item list-group-item-action ${index === 0 ? 'active' : ''}`;
        item.href = `/detail/${suggestion.id}`;
        item.textContent = suggestion.title;
        container.appendChild(item);
    });

    searchInput.parentNode.style.position = 'relative';
    searchInput.parentNode.appendChild(container);
}

function hideAutocomplete() {
    const existing = document.querySelector('.autocomplete-suggestions');
    if (existing) {
        existing.remove();
    }
}

// 价格范围验证
function initPriceValidation() {
    const minPriceInput = document.querySelector('input[name="min_price"]');
    const maxPriceInput = document.querySelector('input[name="max_price"]');

    if (minPriceInput && maxPriceInput) {
        minPriceInput.addEventListener('change', validatePriceRange);
        maxPriceInput.addEventListener('change', validatePriceRange);
    }
}

function validatePriceRange() {
    const minPrice = parseInt(document.querySelector('input[name="min_price"]').value) || 0;
    const maxPrice = parseInt(document.querySelector('input[name="max_price"]').value) || 0;

    if (maxPrice > 0 && minPrice > maxPrice) {
        alert('最低价格不能高于最高价格');
        document.querySelector('input[name="min_price"]').value = '';
    }
}

// 显示Toast消息
function showToast(message, type = 'info') {
    // 简单的Toast实现
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    toast.style.top = '20px';
    toast.style.right = '20px';
    toast.style.zIndex = '1060';
    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
        if (toast.parentNode) {
            toast.remove();
        }
    }, 3000);
}

// 工具函数
function formatPrice(price) {
    if (!price) return '价格面议';
    return '¥' + price.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN');
}

// 图片懒加载
function initLazyLoading() {
    const lazyImages = [].slice.call(document.querySelectorAll('img.lazy'));

    if ('IntersectionObserver' in window) {
        const lazyImageObserver = new IntersectionObserver(function(entries, observer) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    const lazyImage = entry.target;
                    lazyImage.src = lazyImage.dataset.src;
                    lazyImage.classList.remove('lazy');
                    lazyImageObserver.unobserve(lazyImage);
                }
            });
        });

        lazyImages.forEach(function(lazyImage) {
            lazyImageObserver.observe(lazyImage);
        });
    }
}

// 平滑滚动
function smoothScrollTo(target) {
    const targetElement = document.querySelector(target);
    if (!targetElement) return;

    const targetPosition = targetElement.offsetTop;
    const startPosition = window.pageYOffset;
    const distance = targetPosition - startPosition;
    const duration = 500;
    let start = null;

    function animation(currentTime) {
        if (start === null) start = currentTime;
        const timeElapsed = currentTime - start;
        const run = ease(timeElapsed, startPosition, distance, duration);
        window.scrollTo(0, run);
        if (timeElapsed < duration) requestAnimationFrame(animation);
    }

    function ease(t, b, c, d) {
        t /= d / 2;
        if (t < 1) return c / 2 * t * t + b;
        t--;
        return -c / 2 * (t * (t - 2) - 1) + b;
    }

    requestAnimationFrame(animation);
}

// 回到顶部按钮
function initBackToTop() {
    const backToTop = document.createElement('button');
    backToTop.innerHTML = '<i class="fas fa-chevron-up"></i>';
    backToTop.className = 'btn btn-primary back-to-top';
    backToTop.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 1000;
        width: 50px;
        height: 50px;
        border-radius: 50%;
        display: none;
        align-items: center;
        justify-content: center;
    `;

    backToTop.addEventListener('click', () => {
        smoothScrollTo('body');
    });

    document.body.appendChild(backToTop);

    window.addEventListener('scroll', () => {
        if (window.pageYOffset > 300) {
            backToTop.style.display = 'flex';
        } else {
            backToTop.style.display = 'none';
        }
    });
}

// 表单验证增强
function initFormValidation() {
    const forms = document.querySelectorAll('form[novalidate]');

    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateEnhancedForm(this)) {
                e.preventDefault();
                showFormErrors(this);
            }
        });

        // 实时验证
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                validateField(this);
            });

            input.addEventListener('input', function() {
                clearFieldError(this);
            });
        });
    });
}

function validateEnhancedForm(form) {
    let isValid = true;
    const fields = form.querySelectorAll('[required], input[type="email"], input[type="tel"]');

    fields.forEach(field => {
        if (!validateField(field)) {
            isValid = false;
        }
    });

    return isValid;
}

function validateField(field) {
    let isValid = true;
    let message = '';

    // 清除之前的错误状态
    clearFieldError(field);

    // 必填验证
    if (field.hasAttribute('required') && !field.value.trim()) {
        isValid = false;
        message = '此字段为必填项';
    }
    // 邮箱验证
    else if (field.type === 'email' && field.value.trim()) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(field.value.trim())) {
            isValid = false;
            message = '请输入有效的邮箱地址';
        }
    }
    // 电话验证
    else if (field.type === 'tel' && field.value.trim()) {
        const phoneRegex = /^1[3-9]\d{9}$/;
        if (!phoneRegex.test(field.value.trim())) {
            isValid = false;
            message = '请输入有效的手机号码';
        }
    }

    if (!isValid) {
        showFieldError(field, message);
    }

    return isValid;
}

function showFieldError(field, message) {
    field.classList.add('is-invalid');

    let feedback = field.parentNode.querySelector('.invalid-feedback');
    if (!feedback) {
        feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        field.parentNode.appendChild(feedback);
    }

    feedback.textContent = message;
}

function clearFieldError(field) {
    field.classList.remove('is-invalid');
    const feedback = field.parentNode.querySelector('.invalid-feedback');
    if (feedback) {
        feedback.remove();
    }
}

function showFormErrors(form) {
    const firstInvalid = form.querySelector('.is-invalid');
    if (firstInvalid) {
        firstInvalid.focus();
        smoothScrollTo(`#${firstInvalid.id}`);
    }
}

// 收藏功能
function initCollectButtons() {
    // 处理收藏按钮点击事件
    const collectButtons = document.querySelectorAll('.collect-btn');

    collectButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();

            const houseId = this.getAttribute('data-house-id');
            const icon = this.querySelector('i');
            const originalHtml = this.innerHTML;

            // 显示加载状态
            this.disabled = true;
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

            // 发送AJAX请求
            fetch(this.href, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => {
                if (response.ok) {
                    return response.json();
                }
                throw new Error('Network response was not ok.');
            })
            .then(data => {
                // 切换收藏状态图标
                if (icon.classList.contains('far')) {
                    // 从空心变实心
                    icon.classList.remove('far');
                    icon.classList.add('fas', 'text-danger');
                    showToast('收藏成功', 'success');
                } else {
                    // 从实心变空心
                    icon.classList.remove('fas', 'text-danger');
                    icon.classList.add('far');
                    showToast('已取消收藏', 'info');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('操作失败', 'error');
            })
            .finally(() => {
                this.disabled = false;
                this.innerHTML = originalHtml;
            });
        });
    });
}

// 预约功能
function initAppointmentButtons() {
    const appointmentButtons = document.querySelectorAll('.appointment-btn');

    appointmentButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();

            const houseId = this.getAttribute('data-house-id');

            // 跳转到预约页面
            window.location.href = `/appointment/${houseId}`;
        });
    });
}
