const number = new Date().getYear() + 1900
const updateSlug = ev => {
  const value = ev.target.value
  let slug = value.replace(/\W+/g, '-').toLowerCase()
  if (slug && (slug.indexOf(number) == -1))
    slug += "-" + number
  if (slug && slug !== `--${number}`)
    document.querySelector("#id_slug").value = slug
}
document.querySelectorAll("#organiser input").forEach(element => {
  element.addEventListener("input", updateSlug)
})
document.querySelector("#id_slug").addEventListener("input", ev => {
  document.querySelectorAll("#organiser input").forEach(element => {
    element.removeEventListener("input", updateSlug)
  })
})
