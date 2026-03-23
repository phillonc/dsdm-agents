import { useState } from 'react';
import './AddItemForm.css';

export default function AddItemForm({ onAdd, categories }) {
  const [text, setText] = useState('');
  const [category, setCategory] = useState('Other');
  const [quantity, setQuantity] = useState(1);

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed) return;
    onAdd(trimmed, category, quantity);
    setText('');
    setQuantity(1);
  };

  return (
    <form className="add-form" onSubmit={handleSubmit}>
      <div className="form-row">
        <input
          type="text"
          className="item-input"
          placeholder="Add an item..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          autoComplete="off"
        />
        <button type="submit" className="add-btn">Add</button>
      </div>
      <div className="form-options">
        <select
          className="category-select"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        >
          {categories.map(cat => (
            <option key={cat} value={cat}>{cat}</option>
          ))}
        </select>
        <div className="quantity-control">
          <label>Qty:</label>
          <input
            type="number"
            className="quantity-input"
            min="1"
            max="99"
            value={quantity}
            onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
          />
        </div>
      </div>
    </form>
  );
}
