def generate_quotation_number(self):
    from sale.models import SaleInvoice
    if not self.quotation_number and self.status == self.STATUS_SALES_TEAM_PENDING and not self.is_sales_approved:
        prefix = "QN"

        # Get last quotation number from DB
        last = (SaleInvoice.objects.exclude(
            quotation_number__isnull=True).order_by("-id").first())

        if last and last.quotation_number:
            # Example last.quotation_number = "QN24"
            try:
                last_num = int(last.quotation_number.replace(prefix, ""))
            except ValueError:
                last_num = 1
        else:
            last_num = 1

        new_num = last_num + 1
        self.quotation_number = f"{prefix}{new_num}"

        SaleInvoice.objects.filter(pk=self.pk).update(
            quotation_number=self.quotation_number)


def generate_perfoma_invoice_number(self):
    from sale.models import SaleInvoice
    if not self.perfoma_invoice_number and self.has_tax == False:
        prefix = "AJM-"

        # Get last perfoma invoice number from DB
        last = (SaleInvoice.objects.exclude(
            perfoma_invoice_number__isnull=True).order_by("-id").first())

        if last and last.perfoma_invoice_number:
            # Example last.perfoma_invoice_number = "PI24"
            try:
                last_num = int(last.perfoma_invoice_number.replace(prefix, ""))
            except ValueError:
                last_num = 2000
        else:
            last_num = 2000

        new_num = last_num + 1
        self.perfoma_invoice_number = f"{prefix}{new_num}"

        SaleInvoice.objects.filter(pk=self.pk).update(
            perfoma_invoice_number=self.perfoma_invoice_number)

def generate_invoice_number(self):
    from sale.models import SaleInvoice
    if not self.invoice_no:
        prefix = "AJM-"

        # Get last perfoma invoice number from DB
        last = (SaleInvoice.objects.exclude(invoice_no__isnull=True).order_by("-id").first())

        if last and last.invoice_no:
            try:
                last_num = int(last.invoice_no.replace(prefix, ""))
            except ValueError:
                last_num = 2000
        else:
            last_num = 2000

        new_num = last_num + 1
        self.invoice_no = f"{prefix}{new_num}"

        SaleInvoice.objects.filter(pk=self.pk).update(
            invoice_no=self.invoice_no)