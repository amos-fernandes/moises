class ImeAtcoinPayment {
    constructor(apiKey) {
        this.apiKey = apiKey;
    }

    async createPayment(amount, currency) {
        // Lógica para criar um pagamento
    }

    async verifyPayment(paymentId) {
        // Lógica para verificar um pagamento
    }
}

module.exports = ImeAtcoinPayment;