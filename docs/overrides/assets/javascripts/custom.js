const debounce = (fn) => {
  let frame;
  return (...params) => {
    if (frame) {
      cancelAnimationFrame(frame);
    }
    frame = requestAnimationFrame(() => {
      fn(...params);
    });
  };
};

const header = document.querySelector(".md-header");
const hero = document.querySelector(".mdx-parallax__group");
const parallax = document.querySelector(".mdx-parallax");
const transition_elements = [
  ...document.querySelectorAll(".mdx-parallax [hidden]"),
];

const updateHtml = () => {
  const aboveContent = parallax.scrollTop < hero.offsetTop + hero.offsetHeight;
  if (aboveContent) {
    header.classList.remove("md-header--shadow");
  } else {
    header.classList.add("md-header--shadow");
  }
};

const show_hidden = () => {
  transition_elements.forEach((element) => {
    const rect = element.getBoundingClientRect();
    const visible =
      rect.top <= (window.innerHeight || document.documentElement.clientHeight);
    if (visible) {
      element.removeAttribute("hidden");
      transition_elements.splice(transition_elements.indexOf(element), 1);
    }
  });
  if (transition_elements.length == 0) {
    parallax.removeEventListener("scroll", show_hidden_debounce);
  }
};

parallax.addEventListener("scroll", debounce(updateHtml), { passive: true });
const show_hidden_debounce = debounce(show_hidden);
parallax.addEventListener("scroll", show_hidden_debounce, { passive: true });
updateHtml();
