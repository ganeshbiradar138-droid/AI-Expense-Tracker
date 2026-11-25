from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

class ExpenseAI:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(lowercase=True, ngram_range=(1, 2))
        self.model = LogisticRegression(max_iter=1500)
        self.ready = False

    def train(self):
        samples = {
            "Food": ["pizza", "burger", "restaurant dinner", "lunch", "breakfast", "groceries", "vegetables", "fruits", "snacks", "coffee", "tea", "dominos", "food delivery", "swiggy", "zomato", "dinner"],
            "Transport": ["uber", "ola", "taxi", "auto", "bus ticket", "train ticket", "petrol", "diesel", "fuel", "metro", "parking", "bike service", "rickshaw"],
            "Shopping": ["shirt", "shoes", "clothes", "amazon purchase", "shopping", "headphones", "watch", "bag", "electronics", "mall", "dress"],
            "Entertainment": ["movie ticket", "cinema", "netflix", "spotify", "game", "gaming", "concert", "music subscription"],
            "Bills": ["electricity bill", "water bill", "internet bill", "mobile recharge", "phone bill", "rent", "gas bill", "wifi"],
            "Education": ["college fees", "books", "notebook", "exam fees", "course", "tuition", "school fees", "stationery"],
            "Healthcare": ["doctor", "medicine", "hospital", "pharmacy", "medical", "dental", "checkup", "health"],
            "Travel": ["hotel", "flight", "trip", "vacation", "tour", "travel", "resort", "tourist"],
            "Other": ["gift", "donation", "miscellaneous", "repair", "other"]
        }
        texts, labels = [], []
        for category, items in samples.items():
            for item in items:
                texts.append(item)
                labels.append(category)
        X = self.vectorizer.fit_transform(texts)
        self.model.fit(X, labels)
        self.ready = True

    def predict(self, text):
        if not self.ready:
            self.train()
        return self.model.predict(self.vectorizer.transform([text]))[0]

    def confidence(self, text):
        if not self.ready:
            self.train()
        probabilities = self.model.predict_proba(self.vectorizer.transform([text]))[0]
        return float(max(probabilities))
