import './CategoryFilter.css';

export default function CategoryFilter({ categories, active, onChange, items }) {
  const getCategoryCount = (cat) => {
    if (cat === 'All') return items.length;
    return items.filter(item => item.category === cat).length;
  };

  const activeCategories = ['All', ...categories.filter(cat =>
    items.some(item => item.category === cat)
  )];

  if (items.length === 0) return null;

  return (
    <div className="category-filter">
      {activeCategories.map(cat => (
        <button
          key={cat}
          className={`filter-chip ${active === cat ? 'active' : ''}`}
          onClick={() => onChange(cat)}
        >
          {cat}
          <span className="chip-count">{getCategoryCount(cat)}</span>
        </button>
      ))}
    </div>
  );
}
