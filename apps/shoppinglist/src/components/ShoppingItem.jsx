import { useState } from 'react';
import './ShoppingItem.css';

export default function ShoppingItem({
  item,
  isEditing,
  onToggle,
  onDelete,
  onEdit,
  onUpdate,
  categories,
}) {
  const [editText, setEditText] = useState(item.text);
  const [editCategory, setEditCategory] = useState(item.category);
  const [editQuantity, setEditQuantity] = useState(item.quantity);

  const handleSave = () => {
    const trimmed = editText.trim();
    if (!trimmed) return;
    onUpdate(item.id, {
      text: trimmed,
      category: editCategory,
      quantity: editQuantity,
    });
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSave();
    if (e.key === 'Escape') onEdit(null);
  };

  if (isEditing) {
    return (
      <li className="shopping-item editing">
        <input
          type="text"
          className="edit-input"
          value={editText}
          onChange={(e) => setEditText(e.target.value)}
          onKeyDown={handleKeyDown}
          autoFocus
        />
        <select
          className="edit-category"
          value={editCategory}
          onChange={(e) => setEditCategory(e.target.value)}
        >
          {categories.map(cat => (
            <option key={cat} value={cat}>{cat}</option>
          ))}
        </select>
        <input
          type="number"
          className="edit-quantity"
          min="1"
          max="99"
          value={editQuantity}
          onChange={(e) => setEditQuantity(Math.max(1, parseInt(e.target.value) || 1))}
        />
        <div className="edit-actions">
          <button className="save-btn" onClick={handleSave}>Save</button>
          <button className="cancel-btn" onClick={() => onEdit(null)}>Cancel</button>
        </div>
      </li>
    );
  }

  return (
    <li className={`shopping-item ${item.completed ? 'completed' : ''}`}>
      <div className="item-content" onClick={() => onToggle(item.id)}>
        <input
          type="checkbox"
          className="item-checkbox"
          checked={item.completed}
          onChange={() => onToggle(item.id)}
          onClick={(e) => e.stopPropagation()}
        />
        <div className="item-details">
          <span className="item-text">{item.text}</span>
          <div className="item-meta">
            <span className="item-category">{item.category}</span>
            {item.quantity > 1 && (
              <span className="item-quantity">x{item.quantity}</span>
            )}
          </div>
        </div>
      </div>
      <div className="item-actions">
        <button
          className="edit-btn"
          onClick={() => onEdit(item.id)}
          title="Edit"
        >
          Edit
        </button>
        <button
          className="delete-btn"
          onClick={() => onDelete(item.id)}
          title="Delete"
        >
          Delete
        </button>
      </div>
    </li>
  );
}
