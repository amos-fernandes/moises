"""
🌍 SISTEMA SOCIAL - MÓDULO HUMANITÁRIO
Integração do sistema neural com propósito social
"""

from datetime import datetime
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class HumanitarianSystem:
    """
    Sistema Humanitário integrado ao Neural Trading
    Transforma lucros em impacto social real
    """
    
    def __init__(self):
        self.social_fund = 0.0
        self.beneficiaries = []
        self.donations_made = 0.0
        self.families_helped = 0
        self.impact_metrics = {}
        
        # Configurações
        self.donation_percentage = 0.20  # 20% dos lucros
        self.monthly_per_family = 500.0  # R$ 500 por família/mês
        self.emergency_fund = 0.0
        
        logger.info("🌟 Sistema Humanitário inicializado")
    
    def calculate_social_allocation(self, trading_profit: float) -> Dict[str, float]:
        """
        Calcula alocação social dos lucros do trading
        """
        
        social_amount = trading_profit * self.donation_percentage
        emergency_amount = social_amount * 0.30  # 30% para emergências
        regular_amount = social_amount * 0.70    # 70% para doações regulares
        
        allocation = {
            "total_profit": trading_profit,
            "social_percentage": self.donation_percentage,
            "social_amount": social_amount,
            "regular_fund": regular_amount,
            "emergency_fund": emergency_amount,
            "families_can_help": int(regular_amount / self.monthly_per_family)
        }
        
        # Atualizar fundos
        self.social_fund += regular_amount
        self.emergency_fund += emergency_amount
        
        logger.info(f"💰 Lucro social alocado: R$ {social_amount:.2f}")
        
        return allocation
    
    def register_beneficiary(self, family_data: Dict[str, Any]) -> bool:
        """
        Registra nova família beneficiária
        """
        
        required_fields = ["name", "family_size", "monthly_need", "contact", "story"]
        
        if not all(field in family_data for field in required_fields):
            logger.error("❌ Dados incompletos para registro")
            return False
        
        beneficiary = {
            "id": len(self.beneficiaries) + 1,
            "registration_date": datetime.now(),
            "status": "active",
            "total_received": 0.0,
            "months_helped": 0,
            **family_data
        }
        
        self.beneficiaries.append(beneficiary)
        self.families_helped += 1
        
        logger.info(f"👥 Nova família registrada: {family_data['name']}")
        
        return True
    
    def process_monthly_donations(self) -> Dict[str, Any]:
        """
        Processa doações mensais automáticas
        """
        
        active_beneficiaries = [b for b in self.beneficiaries if b["status"] == "active"]
        total_needed = len(active_beneficiaries) * self.monthly_per_family
        
        if self.social_fund < total_needed:
            logger.warning(f"⚠️ Fundo insuficiente: R$ {self.social_fund:.2f} < R$ {total_needed:.2f}")
            return {"status": "insufficient_funds", "shortfall": total_needed - self.social_fund}
        
        donations_processed = []
        
        for beneficiary in active_beneficiaries:
            donation = {
                "beneficiary_id": beneficiary["id"],
                "family_name": beneficiary["name"],
                "amount": self.monthly_per_family,
                "date": datetime.now(),
                "type": "monthly_support"
            }
            
            # Atualizar dados do beneficiário
            beneficiary["total_received"] += self.monthly_per_family
            beneficiary["months_helped"] += 1
            beneficiary["last_donation"] = datetime.now()
            
            donations_processed.append(donation)
            
            # Debitar do fundo
            self.social_fund -= self.monthly_per_family
            self.donations_made += self.monthly_per_family
        
        result = {
            "status": "success",
            "donations_processed": len(donations_processed),
            "total_donated": len(donations_processed) * self.monthly_per_family,
            "remaining_fund": self.social_fund,
            "donations": donations_processed
        }
        
        logger.info(f"💝 {len(donations_processed)} famílias atendidas este mês")
        
        return result
    
    def emergency_assistance(self, beneficiary_id: int, amount: float, reason: str) -> bool:
        """
        Assistência de emergência
        """
        
        if self.emergency_fund < amount:
            logger.error(f"❌ Fundo emergencial insuficiente: R$ {self.emergency_fund:.2f}")
            return False
        
        beneficiary = next((b for b in self.beneficiaries if b["id"] == beneficiary_id), None)
        
        if not beneficiary:
            logger.error(f"❌ Beneficiário {beneficiary_id} não encontrado")
            return False
        
        # Processar emergência
        emergency = {
            "date": datetime.now(),
            "amount": amount,
            "reason": reason,
            "type": "emergency"
        }
        
        if "emergencies" not in beneficiary:
            beneficiary["emergencies"] = []
        
        beneficiary["emergencies"].append(emergency)
        beneficiary["total_received"] += amount
        
        self.emergency_fund -= amount
        self.donations_made += amount
        
        logger.info(f"🚨 Emergência processada: R$ {amount:.2f} para {beneficiary['name']}")
        
        return True
    
    def get_impact_report(self) -> Dict[str, Any]:
        """
        Relatório de impacto social
        """
        
        active_families = len([b for b in self.beneficiaries if b["status"] == "active"])
        total_people_helped = sum(b["family_size"] for b in self.beneficiaries)
        
        # Calcular médias
        avg_months_helped = sum(b["months_helped"] for b in self.beneficiaries) / len(self.beneficiaries) if self.beneficiaries else 0
        avg_per_family = sum(b["total_received"] for b in self.beneficiaries) / len(self.beneficiaries) if self.beneficiaries else 0
        
        report = {
            "summary": {
                "total_families_registered": len(self.beneficiaries),
                "active_families": active_families,
                "total_people_helped": total_people_helped,
                "total_donated": self.donations_made,
                "current_social_fund": self.social_fund,
                "current_emergency_fund": self.emergency_fund
            },
            "averages": {
                "months_helped_per_family": round(avg_months_helped, 1),
                "total_per_family": round(avg_per_family, 2),
                "monthly_capacity": int(self.social_fund / self.monthly_per_family)
            },
            "fund_status": {
                "can_help_families": int(self.social_fund / self.monthly_per_family),
                "months_sustainability": round(self.social_fund / (active_families * self.monthly_per_family), 1) if active_families > 0 else 0,
                "emergency_coverage": self.emergency_fund
            },
            "timestamp": datetime.now()
        }
        
        return report
    
    def generate_success_stories(self) -> List[Dict[str, Any]]:
        """
        Gera histórias de sucesso dos beneficiários
        """
        
        stories = []
        
        for beneficiary in self.beneficiaries:
            if beneficiary["months_helped"] >= 3:  # Pelo menos 3 meses de ajuda
                
                story = {
                    "family_name": beneficiary["name"],
                    "family_size": beneficiary["family_size"],
                    "months_helped": beneficiary["months_helped"],
                    "total_received": beneficiary["total_received"],
                    "story": beneficiary.get("story", ""),
                    "impact": f"Família de {beneficiary['family_size']} pessoas ajudada por {beneficiary['months_helped']} meses",
                    "monthly_value": self.monthly_per_family
                }
                
                stories.append(story)
        
        return sorted(stories, key=lambda x: x["months_helped"], reverse=True)
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Status completo do sistema humanitário
        """
        
        return {
            "system_active": True,
            "donation_percentage": f"{self.donation_percentage * 100}%",
            "families_in_program": len(self.beneficiaries),
            "monthly_capacity": int(self.social_fund / self.monthly_per_family),
            "total_impact": {
                "families_helped": self.families_helped,
                "total_donated": self.donations_made,
                "people_impacted": sum(b["family_size"] for b in self.beneficiaries)
            },
            "fund_health": "healthy" if self.social_fund > 5000 else "low" if self.social_fund > 1000 else "critical"
        }

# Instância global do sistema humanitário
humanitarian_system = HumanitarianSystem()

def integrate_with_trading_system(trading_profit: float):
    """
    Integração com sistema de trading para doações automáticas
    """
    
    if trading_profit > 0:
        allocation = humanitarian_system.calculate_social_allocation(trading_profit)
        logger.info(f"🌟 Impacto social: {allocation['families_can_help']} famílias podem ser ajudadas")
        return allocation
    
    return None